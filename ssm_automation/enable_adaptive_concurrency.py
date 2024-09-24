import botocore
import logging
import boto3
import os

from hs_service.aws.dynamodb import DynamoDB
from argparse import ArgumentParser
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ADAPTIVE_RETRY = Config(retries={"max_attempts": 5, "mode": "adaptive"})


def enable_adaptive_concurrency(client):
    try:
        response = client.update_service_setting(
            SettingId='/ssm/automation/enable-adaptive-concurrency',
            SettingValue='True'
        )
        return response
    except ClientError as err:
        logger.exception(f"Failed to update service setting: {err}")
        return None


def get_target_account_sts_credentials(account_id):
    """
    Function to get credentials for target account
    :param account_id:
    :return credentials:
    """
    target_role_arn = f"arn:aws:iam::{account_id}:role/AWS_PLATFORM_ADMIN"
    logger.info(f"Attempting to assume role: {target_role_arn}")

    sts_client = boto3.client("sts")
    try:
        credentials = sts_client.assume_role(
            RoleArn=target_role_arn, RoleSessionName="SSM_Automation"
        )["Credentials"]
    except ClientError as err:
        logger.exception(f"Failed to assume role {target_role_arn}: {err}")
        raise

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


def get_accounts_by_types(account_types):
    ddb = DynamoDB(f"{os.getenv('DDB_PREFIX', None)}-DYN_METADATA")

    base_expression = (
        Attr("status").eq("Active")
        | Attr("status").eq("Provision")
        | Attr("status").eq("Provisioning")
        | Attr("status").eq("Quarantine")
    ) & Attr("account-type").is_in(account_types)

    accounts = ddb.get_all_entries(filter_expression=base_expression)
    accounts = sorted(accounts, key=lambda x: x["account"], reverse=False)

    return accounts


if __name__ == "__main__":
    # Accepting CLI args
    parser = ArgumentParser()
    parser.add_argument(
        "--no-dry-run", help="if not provided dry run mode is on", action="store_true"
    )
    parser.add_argument(
        "--account-types-inclusive",
        nargs="+",
        help="account types that will be targeted. e.g. Connected, Security",
        default=["Connected"],  # Default to only "Connected" if not provided
    )

    args = parser.parse_args()

    logger.info(f"Dry run mode is {'off' if args.no_dry_run else 'on'}")
    logger.info(f"Targeting account types: {', '.join(args.account_types_inclusive)}")

    processed_list = [
        [
            "account-id",
            "account-type",
            "environment-type",
            "region",
            "status",
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

    accounts = get_accounts_by_types(args.account_types_inclusive)
    total_accounts = len(accounts)
    index = 0

    for account in accounts:
        if "region" not in account:
            logger.warning(f"empty region for account {account['account']}")
            account_region = "eu-west-1"
        else:
            account_region = account["region"]

        try:
            client = get_client_by_service(account_region, account["account"], "ssm")
            response = enable_adaptive_concurrency(client)
            request_status = "UPDATED" if response else "FAILED"

        except ClientError as err:
            logger.exception(err)
            request_status = "CLIENT_ERROR"
        except Exception as err:
            logger.exception(err)
            request_status = "GENERIC_ERROR"

        index += 1
        processed_list.append(
            [
                account["account"],
                account["account-type"] if "account-type" in account else None,
                account["environment-type"] if "environment-type" in account else None,
                account_region,
                account["status"],
                request_status,
            ]
        )

        logger.info(f"{(index / total_accounts) * 100:.2f}% completed")

    if not args.no_dry_run:
        logger.info("The service setting would have been updated but dry run is set to True")
    else:
        logger.info("Service setting updated successfully")
