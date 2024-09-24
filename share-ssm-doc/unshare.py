from argparse import ArgumentParser
import datetime
import logging
import sys
import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from hs_service.aws.dynamodb import DynamoDB
from time import sleep
import botocore.exceptions

hub_name = ""
lmb_spoke_account = {
    "WH-0001": ["Z0S4", 495416159460],
    "WH-0002": ["Y0MI", 974944152507],
    "WH-0003": ["01AW", 768961172930],
}

regions = [
    "ap-southeast-3",
    "ap-southeast-1",
    "ap-southeast-2",
    "ca-west-1",
    "us-east-1",
    "us-east-2",
    "eu-west-1",
    "eu-west-2",
    "eu-central-1",
]

document_names = [
    "BpPlatformServices_DomainJoinAutomation",
    "BpPlatformServices_RHEL_DomainJoin",
    "BpPlatformServices_SLES_DomainJoin",
    "BpPlatformServices_Ubuntu_DomainJoin",
    "BpPlatformServices_WIN_DomainJoin",
]

file_name = f"./unshare-ssm-doc-logfile {datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"
logging.basicConfig(
    filename=file_name,
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))
BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


def get_ssm_document_shares(client, document_name, region):
    try:
        # Retrieve the permissions of the SSM document
        response = client.describe_document_permission(
            Name=document_name, PermissionType="Share"
        )

        # Extract the account IDs from the response
        shared_accounts = response.get("AccountIds", [])
        return shared_accounts

    except Exception as e:
        logger.error(f"Error fetching document permissions: {e}")
        return []


def unshare_ssm_document(client, document_name, unmatch_account, region, dry_run=True):
    if region == "N/A":
        logger.error(f"region missing in {unmatch_account}")
    if dry_run:
        logger.info(
            f"DRY RUN: Would unshare {(unmatch_account)} account from {document_name} in {region}"
        )

        return
    else:
        try:
            retry_with_exponential_backoff(
                lambda: client.modify_document_permission(
                    Name=document_name,
                    PermissionType="Share",
                    AccountIdsToAdd=[],
                    AccountIdsToRemove=[account],
                )
            )
            logger.info(
                f"Successfully unshared {(unmatch_account)} account from {document_name} in {region}"
            )
        except Exception as e:
            logger.error(
                f"Failed to unshare accounts from {document_name} in {region}: {e}"
            )


def retry_with_exponential_backoff(function, max_retries=5, initial_delay=1):
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            function()
            return
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] in ["Throttling", "ThrottlingException"]:
                logger.warning(
                    f"Throttling error occurred. Retrying in {delay} seconds..."
                )
                sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError(
        f"Failed to complete operation after {max_retries} retries due to throttling."
    )


def fetch_accounts_from_metadata(hub_name, region):
    try:
        logger.info(
            f"Fetching spoke accounts from table {hub_name}-DYN_METADATA in {region}"
        )
        dynamodb = DynamoDB(f"{hub_name}-DYN_METADATA")

        filter_expression = (
            Attr("status").eq("Active")
            & Attr("account-type").ne("Connected")
            & Attr("region").eq(region)
        )
        return dynamodb.get_all_entries(filter_expression=filter_expression)
    except Exception as e:
        logger.error(f"Failed to fetch accounts from {account}: {e}")


def fetch_accounts_by_account_id(hub_name, account):
    try:
        dynamodb = DynamoDB(f"{hub_name}-DYN_METADATA")
        filter_expression = Attr("status").eq("Active") & Attr("account").eq(account)

        return dynamodb.get_all_entries(filter_expression=filter_expression)
    except Exception as e:
        logger.error(f"Failed to fetch accounts from {account}: {e}")


def assume_role():
    try:
        role_arn = (
            f"arn:aws:iam::{lmb_spoke_account[hub_name][1]}:role/AWS_PLATFORM_ADMIN"
        )
        role_session_name = "SHARE-SSM-DOC"
        sts_client = boto3.client("sts")
        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
        return response["Credentials"]

    except Exception as e:
        logger.error(f"No AWS credentials found: {e}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-e",
        "--hub_env",
        type=str,
        help="Provide hub name example: WH-0002",
        required=True,
    )
    parser.add_argument("--no-dry-run", help="Dry run", action="store_false")
    args = parser.parse_args()
    hub_name = args.hub_env
    logger.info(f"Dry Run : {args.no_dry_run}")
    fieldnames = ["document_name", "account", "account-type", "aws-region"]
    credentials = assume_role()
    all_ssm_shared_accounts = set()
    for region in regions:
        for document_name in document_names:
            client = boto3.client(
                "ssm",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=region,
            )
            ddb_response = fetch_accounts_from_metadata(hub_name, region)
            ddb_accounts = set(account["account"] for account in ddb_response)
            region_shared_accounts = get_ssm_document_shares(
                client, document_name, region
            )
            for account_id in region_shared_accounts:
                all_ssm_shared_accounts.add(account_id)
            unmatching_accounts = all_ssm_shared_accounts.intersection(ddb_accounts)
            if unmatching_accounts:
                print(f"Found {len(unmatching_accounts)} unmatch accounts.")
                logger.info(f"Found {len(unmatching_accounts)} unmatch accounts.")

                for account in unmatching_accounts:
                    unmatch_account = fetch_accounts_by_account_id(hub_name, account)
                    logger.info(
                        f"{document_name},{unmatch_account[0]['account']},{unmatch_account[0]['account-type']}, {region}"
                    )
                    unshare_ssm_document(
                        client,
                        document_name,
                        unmatch_account[0]["account"],
                        unmatch_account[0]["region"],
                        args.no_dry_run,
                    )
            else:
                print("No accounts to unshare.")
