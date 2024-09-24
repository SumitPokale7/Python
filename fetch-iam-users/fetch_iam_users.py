import csv
import boto3
import logging
import argparse
from boto3.dynamodb.conditions import Attr
from datetime import datetime


parser = argparse.ArgumentParser()
parser.add_argument(
    "--hub-account", type=str, required=True, help="The Hub Account Name"
)
parser.add_argument(
    "--role-to-assume", type=str, required=True, help="The IAM Role to assume"
)
args = parser.parse_args()
IAM_ROLE_TO_ASSUME = args.role_to_assume
HUB_ACCOUNT = args.hub_account


logging.basicConfig(
    filename=f'fetch_iam_users_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{HUB_ACCOUNT}.log',
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S",
    level=logging.INFO,
)
console_handler = logging.StreamHandler()
logger = logging.getLogger()
logger.addHandler(console_handler)


def fetch_accounts_from_dynamo_db(table_name):
    # Fetches account IDs from a specified DynamoDB table.
    account_ids = []
    dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
    table = dynamodb.Table(table_name)
    scan_response = table.scan(
        FilterExpression=Attr("it-service").eq("AWS Platform")
        & Attr("status").eq("Active")
    )
    for table_item in scan_response["Items"]:
        account_ids.append(f"{table_item['account-name']}--{table_item['account']}")
    return account_ids


def get_credentials(account_id):
    # Retrieves credentials for a given AWS account ID.
    sts_client = boto3.client("sts")
    spoke_role_arn = f"arn:aws:iam::{account_id}:role/{IAM_ROLE_TO_ASSUME}"
    creds = sts_client.assume_role(
        RoleArn=spoke_role_arn, RoleSessionName="Fetch-IAM-Users"
    )
    return creds


def get_assumed_session(creds):
    # Establishes an assumed session with the provided credentials.
    session = boto3.session.Session(
        region_name="eu-west-1",
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
    )
    return session


def write_to_csv(data, filename):
    # Writes provided data to a CSV file with the given filename.
    headers = ["Account Name & ID", "Users"]
    with open(filename, "a", newline="") as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=headers)
        if output_file.tell() == 0:
            dict_writer.writeheader()
        dict_writer.writerows(data)


def main():
    # Main function that orchestrates the fetching of account IDs, retrieval of credentials, session assumption, and writing data to a CSV file.
    data = []
    try:
        account_ids = fetch_accounts_from_dynamo_db(f"{HUB_ACCOUNT}-DYN_METADATA")
        print(
            f"Number of accounts: {len(account_ids)} and account IDs are {account_ids}"
        )
        for account_id in account_ids:
            try:
                user_list = []
                creds = get_credentials(account_id.split("--")[1])
                session = get_assumed_session(creds)
                iam_client = session.client("iam")
                response = iam_client.list_users()
                logger.info(
                    f"For Account ID {account_id} the users response is {response}"
                )
                if response.get("Users"):
                    for user in response["Users"]:
                        user_list.append(user["UserName"])
                data.append({"Account Name & ID": account_id, "Users": user_list})
            except Exception as exception_message:
                if "AccessDenied" in str(exception_message):
                    data.append(
                        {
                            "Account Name & ID": account_id,
                            "Users": "Access Denied While Assuming Role",
                        }
                    )
                    logger.error(f"Access Denied for Account ID: {account_id}")
                else:
                    raise exception_message
    except Exception as exception_message:
        if "ExpiredTokenException" in str(exception_message):
            logger.error(
                f"Expired Token Exception: {exception_message}, Generate new token and try again."
            )
        else:
            logger.error(exception_message)
    finally:
        if data:
            write_to_csv(
                data,
                f'iam_users_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{HUB_ACCOUNT}.csv',
            )
            logger.info("Data written to csv file")
        else:
            logger.info("No data to write to csv file")


if __name__ == "__main__":
    main()
