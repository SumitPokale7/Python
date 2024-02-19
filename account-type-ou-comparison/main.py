import datetime
import boto3
import argparse
import logging
from hs_service.aws.dynamodb import DynamoDB
from boto3.dynamodb.conditions import Attr
from botocore.config import Config

BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})

# set logger to write to file and console
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=f"{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


# query account in aws organizations and determine its parent ou name
def query_account_parent_ou(account_id):
    client = boto3.client("organizations", config=BOTO3_CONFIG)
    parent = client.list_parents(ChildId=account_id)["Parents"][0]["Id"]
    return client.describe_organizational_unit(OrganizationalUnitId=parent)[
        "OrganizationalUnit"
    ]["Name"]


def fetch_accounts_from_metadata(environment_type, account_type, hub_name):
    dynamodb = DynamoDB(f"{hub_name}-DYN_METADATA")
    filter_expression = Attr("status").eq("Active") & Attr("account-type").eq(
        account_type
    )
    if environment_type:
        filter_expression = filter_expression.__and__(
            Attr("environment-type").eq(environment_type)
        )

    return dynamodb.get_all_entries(filter_expression=filter_expression)


def main(environment_type, account_type, hub_name):
    accounts = fetch_accounts_from_metadata(environment_type, account_type, hub_name)
    for account in accounts:
        account_id = account["account"]
        account_name = account["account-name"]
        account_description = account["account-description"]
        it_service = account["it-service"]
        owner = account["account-owner"]
        parent_ou_name = query_account_parent_ou(account_id)
        logger.info(
            f"{parent_ou_name}, {account_id}, {account_name}, {account_description}, {it_service}, {owner}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--account-type",
        help="The account type to be used for the account type comparison.",
    )
    parser.add_argument(
        "--hub-name", help="The hub name, used for ddb table name, e.g. WH-0001"
    )
    parser.add_argument(
        "--environment-type",
        help="The environment type to be used for the account type comparison.",
        default=None,
    )
    args = parser.parse_args()
    logger.info(
        "Parent OU, Account ID, Account Name, Account Description, IT Service, Owner"
    )
    main(args.environment_type, args.account_type, args.hub_name)
