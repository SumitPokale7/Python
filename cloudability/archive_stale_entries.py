import requests
import logging
from datetime import datetime
import argparse

from extract_stale_entries import fetch_stale_cloudability_accounts, get_access_key

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
DRY_RUN = args.dry_run
cloudability_account = h1_cloudability_account


if HUB_ACCOUNT.upper() == "H2":
    cloudability_account = h2_cloudability_account
elif HUB_ACCOUNT.upper() == "H3":
    cloudability_account = h3_cloudability_account
else:
    cloudability_account = h1_cloudability_account


logging.basicConfig(
    filename=f'archived_cloudability_accounts{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{HUB_ACCOUNT.upper()}.log',
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger()


def create_credentials(account_id):
    logger.info("Attempting to create credential for linked account")
    headers = {"Content-Type": "application/json"}
    payload = {
        "vendorAccountId": account_id,
        "type": "aws_role",
        "roleName": "CIP_Cloudability",
        "parentAccountId": cloudability_account,
    }
    response = requests.post(
        "https://api.cloudability.com/v3/vendors/AWS/accounts",
        headers=headers,
        auth=(get_access_key(), ""),
        json=payload,
    )
    logger.info(response)


def archive_cloudability_account(account_id):
    archive_url = (
        f"https://api.cloudability.com/v3/vendors/AWS/accounts/{account_id}/archive"
    )
    archive_account_response = requests.post(archive_url, auth=(get_access_key(), ""))
    archive_account_response = archive_account_response.json()
    if "result" in archive_account_response:
        logger.info("Check if account has been archived")
        if archive_account_response["result"].get("verification"):
            if (
                archive_account_response["result"]["verification"].get("state")
                == "archived"
            ):
                logger.info(f"Account {account_id} is archived now")
            else:
                logger.warning(f"Unable to archive account {account_id}")
        else:
            logger.warning(f"Account still has no state {account_id}")


def archive_stale_entries():
    print(f"Dry run set to {DRY_RUN}")

    stale_accounts = fetch_stale_cloudability_accounts(cloudability_account, logger)
    logger.info(f"Handling cloudability account {cloudability_account} ...")
    for account in stale_accounts:
        if DRY_RUN:
            if account.get("verification", {}).get("state") == "error":
                logger.info(
                    f"Dry Run: would archive account {account['id']} ... with state {account['verification']['state']}"
                )
            elif account.get("verification", {}) == {}:
                logger.info(
                    f"Dry Run: would archive account {account['id']} ... without state"
                )
        else:
            if account.get("verification", {}).get("state") == "error":
                logger.info(
                    f"Archiving account {account['id']} ... with state {account['verification']['state']}"
                )
                archive_cloudability_account(account["id"])
            elif account.get("verification", {}) == {}:
                logger.info(f"Archiving account {account['id']} ... without state")
                create_credentials(account["id"])
                archive_cloudability_account(account["id"])


if __name__ == "__main__":
    archive_stale_entries()
