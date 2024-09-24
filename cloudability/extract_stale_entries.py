import requests
import logging
from datetime import datetime
import boto3
import argparse

h1_cloudability_account = "423499082931"
h2_cloudability_account = "550590017392"
h3_cloudability_account = "550772936474"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--hub-account",
    type=str,
    required=True,
    default="H1",
    help="The Hub Account Name, H1, H2 or H3, defaults to H1",
)
parser.add_argument(
    "--dry-run",
    action=argparse.BooleanOptionalAction,
    help="Dry run, sets to true if set",
)
args = parser.parse_args()
HUB_ACCOUNT = args.hub_account

if HUB_ACCOUNT.upper() == "H2":
    cloudability_account = h2_cloudability_account
elif HUB_ACCOUNT.upper() == "H3":
    cloudability_account = h3_cloudability_account
else:
    cloudability_account = h1_cloudability_account

logging.basicConfig(
    filename=f'fetch_cloudability_accounts{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{HUB_ACCOUNT.upper()}.log',
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger()


def get_access_key():
    secret_name = "CloudabilityAccessKey"
    sm_client = boto3.client("secretsmanager", region_name="eu-west-1")

    response = sm_client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]


def fetch_stale_cloudability_accounts(cloudability_account, logger=logger):
    # Fetches account IDs from Cloudability.
    url = f"https://api.cloudability.com/v3/vendors/AWS/accounts/{cloudability_account}?include=associatedAccounts"

    response = requests.get(url, auth=(get_access_key(), ""))
    result = response.json()
    # logger.info(result)
    stale_accounts = []
    logger.info("Fetching stale accounts")
    for account in result["result"]["associatedAccounts"]:
        # if account.get("verification", {}).get("state") == "verified":
        if account.get("verification", {}).get("state") == "error":
            state = account["verification"]["state"]
            logger.info(
                f"Fetched stale account: state:{state} account_id:{account['id']}"
            )
            stale_accounts.append(account)
        if account.get("verification", {}) == {}:
            # state = account["verification"]["state"]
            logger.info(
                f"Fetched stale account without state, account_id:{account['id']}"
            )
            stale_accounts.append(account)

    return stale_accounts


if __name__ == "__main__":
    fetch_stale_cloudability_accounts(cloudability_account)
