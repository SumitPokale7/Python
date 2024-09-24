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
class ServiceQuota:
    service_code: str
    quota_code: str
    desired_value: float
    region: str = "us-east-1"

    @staticmethod
    def validate_str(word):
        if not word or word == "":
            return False
        else:
            return True

    @staticmethod
    def validate_float(float_number):
        if not float_number or not type(float_number) is float:
            return False
        else:
            return True

    def __post_init__(self):
        if not ServiceQuota.validate_str(self.service_code):
            raise ValueError(f"service code {self.service_code} is invalid")
        if not ServiceQuota.validate_str(self.quota_code):
            raise ValueError(f"quota code {self.quota_code} is invalid")
        if not ServiceQuota.validate_float(self.desired_value):
            raise ValueError(f"desired value {self.desired_value} is invalid")


@dataclass
class ServiceQuotaManager:
    client: None
    service_quota: ServiceQuota

    def get_service_quota(self):
        _quota = self.client.get_service_quota(
            ServiceCode=self.service_quota.service_code,
            QuotaCode=self.service_quota.quota_code,
        )["Quota"]["Value"]
        if _quota >= service_quota.desired_value:
            logger.warning(
                f"existing quota {_quota} is equal or bigger than desired value {service_quota.desired_value} "
                f"for account {spoke['account']} "
            )
        return _quota

    def increase_quota(self):
        _response = self.client.request_service_quota_increase(
            ServiceCode=self.service_quota.service_code,
            QuotaCode=self.service_quota.quota_code,
            DesiredValue=self.service_quota.desired_value,
        )
        return _response

    def delete_quota(self):
        _response = self.client.delete_service_quota_increase_request_from_template(
            ServiceCode=self.service_quota.service_code,
            QuotaCode=self.service_quota.quota_code,
            AwsRegion="us-east-1",
        )
        return _response

    def list_quota(self):
        _response = self.client.list_requested_service_quota_change_history_by_quota(
            ServiceCode=self.service_quota.service_code,
            QuotaCode=self.service_quota.quota_code,
        )
        return _response


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
    ) & Attr("account-type").ne("Hub")  # in case required & Attr("account").eq("774130573257")

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
        "--service-code", help="Specifies the service identifier", type=str
    )
    parser.add_argument("--quota-code", help="Specifies the quota identifier", type=str)
    parser.add_argument(
        "--desired-value",
        help="Specifies the new, increased value for the quota",
        type=float,
    )
    parser.add_argument(
        "--no-dry-run", help="if not provided dry run mode is on", action="store_true"
    )
    parser.add_argument(
        "--service-region",
        help="service quota increase region",
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

    parser.add_argument(
        "--no-incr-but-list",
        help="if provided only listing quotas ",
        action="store_true",
    )

    args = parser.parse_args()
    service_region = args.service_region

    service_quota = ServiceQuota(
        args.service_code, args.quota_code, args.desired_value, service_region
    )

    logger.info(f"given parameters for quota increase: {service_quota}")

    processed_list = [
        [
            "account-id",
            "account-type",
            "environment-type",
            "region",
            "status",
            "old_value",
            "new_value",
            "request-status",
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
        existing_quota = None
        try:
            client = get_client_by_service(
                service_quota.region
                if service_quota.service_code == "iam"
                else spoke_region,
                spoke["account"],
                "service-quotas",
            )
            service_quota_mgr = ServiceQuotaManager(client, service_quota)
            existing_quota = service_quota_mgr.get_service_quota()

            if existing_quota < service_quota.desired_value:
                if args.no_dry_run:
                    if args.no_incr_but_list:
                        response = service_quota_mgr.list_quota()
                        request_status = [
                            f"{quota['QuotaCode']}-{quota['Status']}"
                            for quota in response["RequestedQuotas"]
                        ]
                    else:
                        response = service_quota_mgr.increase_quota()
                        if "RequestedQuota" in response:
                            request_status = response["RequestedQuota"]["Status"]
                        else:
                            request_status = "APPLIED"
                        logger.info(
                            f"quota increase request: {response['RequestedQuota']['Status']} in "
                            f"{response['RequestedQuota']['QuotaRequestedAtLevel']} level "
                            f"for account {spoke['account']}"
                        )
                else:
                    request_status = "DRY-RUN"
            else:
                request_status = "SKIPPED"

        except ClientError as err:
            logger.exception(err)
            if err.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.critical(
                    f"{err.response['Error']['Code']} for {spoke['account']}"
                )
                response = service_quota_mgr.list_quota()
                request_status = [
                    f"{quota['QuotaCode']}-{quota['Status']}"
                    for quota in response["RequestedQuotas"]
                ]
            else:
                if err.response["Error"]["Code"] == "QuotaExceededException":
                    logger.critical(
                        f"QuotaExceededException is thrown for {spoke['account']}"
                    )
                elif err.response["Error"]["Code"] == "TooManyRequestsException":
                    logger.critical(
                        f"TooManyRequestsException is thrown for {spoke['account']}"
                    )
                elif err.response["Error"]["Code"] == "AccessDenied":
                    logger.critical(f"Access denied for {spoke['account']}")

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
                existing_quota,
                service_quota.desired_value,
                request_status,
            ]
        )

        logger.info(f"the %{(index / total_accounts) * 100:.2f} percent completed")

    # current date and time
    date_time = datetime.now()
    _format = "%Y-%m-%d-%H-%M-%S"

    with open(
        f'{os.getenv("DDB_PREFIX")}_{date_time.strftime(_format)}_{"" if args.no_dry_run else "not_"}processed.csv',
        "w",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerows(processed_list)

    if not args.no_dry_run:
        logger.info("the quota would have been increased but dry run is set to True")
    else:
        logger.info("quota increased successfully")
