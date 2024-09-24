import botocore
import logging
import boto3
import os
import csv

from dataclasses import dataclass
from hs_service.aws.dynamodb import DynamoDB
from argparse import ArgumentParser
from boto3.dynamodb.conditions import Attr
from datetime import datetime
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ADAPTIVE_RETRY = Config(retries={"max_attempts": 5, "mode": "adaptive"})


@dataclass
class CaseManager:
    client: None
    resource: None

    def __init__(self, _client):
        self.client = _client

    def get_support_cases(
        self,
        # status="pending-customer-action",
        subject="Limit Increase: EC2 Systems Manager",
    ):
        _response = self.client.describe_cases()
        _cases = []
        if "cases" in _response and len(_response["cases"]) > 0:
            _cases = [
                f'{case["caseId"]};{case["displayId"]}'
                for case in _response["cases"]
                if case["subject"] == subject
            ]

        return _cases

    def resolve_cases(self, case_ids):
        tmp = []
        for case_id in case_ids:
            _response = self.client.resolve_case(caseId=case_id.split(";")[0])
            tmp.append(
                f"{_response['initialCaseStatus']}-{case_id.split(';')[1]}-{_response['finalCaseStatus']}"
            )

        return tmp


def get_target_account_sts_credentials(account_id):
    """
    Function to get credentials for target account
    :param account_id:
    :return credentials:
    """

    target_role_arn = f"arn:aws:iam::{account_id}:role/CIP_INSPECTOR"

    sts_client = boto3.client("sts")
    credentials = sts_client.assume_role(
        RoleArn=target_role_arn, RoleSessionName="ServiceQuotaManager"
    )["Credentials"]

    return credentials


def get_client_by_service(region, account_id, service_name):
    _credentials = get_target_account_sts_credentials(account_id)

    _client = boto3.client(
        service_name,
        aws_access_key_id=_credentials.get("AccessKeyId"),
        aws_secret_access_key=_credentials.get("SecretAccessKey"),
        aws_session_token=_credentials.get("SessionToken"),
        region_name=region,
        config=ADAPTIVE_RETRY,
    )

    return _client


def get_spokes(account_types=None):
    ddb = DynamoDB(f"{os.getenv('DDB_PREFIX', None)}-DYN_METADATA")

    base_expression = (
        Attr("status").eq("Active")
        | Attr("status").eq("Provision")
        | Attr("status").eq("Provisioning")
        | Attr("status").eq("Quarantine")
    ) & Attr("account-type").ne("Hub")
    if account_types:
        _filter_expression = Attr("account-type").eq(account_types[0])
        for x in account_types:
            _filter_expression = _filter_expression | Attr("account-type").eq(x)

        base_expression = base_expression & _filter_expression

    spoke_accounts = ddb.get_all_entries(filter_expression=base_expression)
    spoke_accounts = sorted(spoke_accounts, key=lambda x: x["account"], reverse=False)

    return spoke_accounts


if __name__ == "__main__":
    # Accepting CLI args
    parser = ArgumentParser()

    parser.add_argument(
        "--no-dry-run", help="if not provided dry run mode is on", action="store_true"
    )
    parser.add_argument(
        "--service-region",
        help="support case region",
        type=str,
        default="us-east-1",
    )
    parser.add_argument(
        "--resumed-spoke",
        help="resume the process where it was left",
        type=str,
        default="000000000000",
    )
    parser.add_argument("--nargs", nargs="+")

    parser.add_argument(
        "--account-types-inclusive",
        nargs="+",
        help="account types that will be targeted. e.g. Connected Unmanaged ",
        default=None,
    )

    args = parser.parse_args()
    # service_region = args.service_region

    processed_list = [
        [
            "account-id",
            "account-type",
            "environment-type",
            "region",
            "cases_status",
            "subject",
            "case_id",
        ]
    ]

    try:
        dev_session = boto3.session.Session(
            profile_name=os.getenv("AWS_DEFAULT_PROFILE", None), region_name="eu-west-1"
        )
    except botocore.exceptions.ProfileNotFound as err:
        raise err

    logger.info(f"profile name: {os.getenv('AWS_DEFAULT_PROFILE', None)}")

    spokes = get_spokes(args.account_types_inclusive)
    total_accounts = len(spokes)
    index = 0

    for spoke in spokes:
        if "region" not in spoke:
            logger.warning(f"empty region for spoke {spoke['account']}")
            spoke_region = "eu-west-1"
        else:
            spoke_region = spoke["region"]

        if spoke["account"] <= args.resumed_spoke:
            index = index + 1
            logger.info(
                f'skipped to process {spoke["account"]} up to {args.resumed_spoke}'
            )
            continue
        request_status = None
        try:
            client = get_client_by_service(
                spoke_region,
                spoke["account"],
                "support",
            )
            case_mgr = CaseManager(client)
            cases = case_mgr.get_support_cases()

            if args.no_dry_run:
                request_status = case_mgr.resolve_cases(cases)
            else:
                request_status = f"DRY-RUN-{cases}"

        except ClientError as err:
            logger.exception(err)
            if err.response["Error"]["Code"] == "CaseIdNotFound":
                logger.critical(f"CaseIdNotFound is thrown for {spoke['account']}")
            request_status = "CLIENT_ERROR"
        except Exception as err:
            logger.exception(err)
            logger.critical(
                f"An unhandled exception has been detected for {spoke['account']}"
            )
            request_status = "GENERIC_ERROR"
        index = index + 1
        processed_list.append(
            [
                spoke["account"],
                spoke["account-type"] if "account-type" in spoke else None,
                spoke["environment-type"] if "environment-type" in spoke else None,
                spoke_region,
                spoke["status"],
                request_status,
            ]
        )

        logger.info(f"the %{(index / total_accounts) * 100:.2f} percent completed")

    # current date and time
    date_time = datetime.now()
    _format = "%Y-%m-%d-%H-%M-%S"

    with open(
        f'case_{os.getenv("DDB_PREFIX")}_{date_time.strftime(_format)}_{"" if args.no_dry_run else "not_"}processed.csv',
        "w",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerows(processed_list)

    if not args.no_dry_run:
        logger.info("the case have been resolved but dry run is set to True")
    else:
        logger.info("support case was resolved successfully")
