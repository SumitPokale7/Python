# enterprise-ce-operations.py
#
# Extracts resources the cloud environments from the enterprise environments based on naming convention '{$CE_NAME}-DELETION-XXXX'
# ---------

import boto3
import botocore
from botocore.exceptions import ClientError
import logging
import csv
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import re
import os

# Define constants for CE names , just update new environment name
ALPHA_CE_ENV_NAMES = ["WU2-A1", "WE1-A1"]
BETA_CE_ENV_NAMES = ["WU2-U1", "WE1-U1", "WU2-B1", "WE1-B1"]
PREPROD_CE_ENV_NAMES = ["WE1-T1", "WU2-T1", "WE1-O2", "WE1-P2", "WU2-P2"]
PROD_CE_ENV_NAMES = ["WE1-O3", "WU2-P3", "WE1-P3", "WU2-P1", "WE1-P1"]
EVERY_CE_ENV_NAMES = (
    ALPHA_CE_ENV_NAMES + BETA_CE_ENV_NAMES + PREPROD_CE_ENV_NAMES + PROD_CE_ENV_NAMES
)

aws_region = os.environ.get("AWS_REGION", "us-east-2")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_session(ce_name, region=aws_region):
    PROFILE = f"{ce_name}-role_DEVOPS"
    try:
        dev_session = boto3.session.Session(profile_name=PROFILE, region_name=region)
    except botocore.exceptions.ProfileNotFound:
        logger.error(f"Profile not found: {PROFILE}")
        return None

    logger.info(f"profile name: {PROFILE}")
    return dev_session


def extract_ces(env_name, region, dry_run=False):
    """
    Extract CEs for a given environment and region, then update the expiration data
    Filter CEs where deleted-on field is empty
    """
    if dry_run:
        logger.info(
            f"Dry run: Extracting CEs for environment {env_name} in region {region}"
        )

    session = get_session(env_name, region)
    if session:
        ddb_resource = session.resource("dynamodb")
        try:
            table = ddb_resource.Table("CLOUD-ENVIRONMENTS")
            response = table.scan(AttributesToGet=["cloud-environment", "deleted-on"])
            ces = [item["cloud-environment"] for item in response["Items"]]

            # Filtering ce's with naming *deletion*
            pattern = r"^.*-DELETION-\d+$"
            filtered_ces = [ce for ce in ces if re.match(pattern, ce)]

            # Filter CEs where deleted-on is empty or not set
            filtered_ces = [
                ce
                for ce in filtered_ces
                if not table.get_item(Key={"cloud-environment": ce})
                .get("Item", {})
                .get("deleted-on")
            ]
            if not dry_run:
                # Updating expiration date for filtered ces (dry-run mode)
                yesterday_date = datetime.now() - timedelta(days=1)
                yesterday_date = yesterday_date.strftime("%d-%m-%Y")
                for ce in filtered_ces:
                    update_expiration_date(table, ce, yesterday_date)

            return filtered_ces
        except ddb_resource.meta.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Table 'CLOUD-ENVIRONMENTS' not found in region {region}")
            return []
    else:
        logger.warning(
            f"Failed to create session for environment {env_name} in region {region}"
        )
        return []


def update_expiration_date(table, ce_name, expiration_date):
    """
    Update the expiration field for a given Cloud Environment in the DynamoDB table.

    :param table_name: The name of the DynamoDB table.
    :param ce_name: The name of the Cloud Environment.
    :param expiration_date: The new expiration date.
    """
    try:
        response = table.update_item(
            Key={"cloud-environment": ce_name},
            UpdateExpression="SET expiration = :exp",
            ExpressionAttributeValues={":exp": expiration_date},
            ReturnValues="UPDATED_NEW",
        )
        logger.info(f"Updated expiration date for {ce_name} to {expiration_date}")
        return response
    except ClientError as e:
        logger.error(
            f"Error updating expiration date for {ce_name}: {e.response['Error']['Message']}"
        )
        return None


def save_report_to_file(report, filename):
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Cloud Environment", "Region"])
        writer.writerows([[ce, region] for ce, region in report])


def main(dry_run=True, env_names=EVERY_CE_ENV_NAMES, csv_filename=None):
    region = aws_region
    all_ces = []
    env_names = args.env_names or env_names
    logger.info(f"Processing environments: {', '.join(env_names)}")
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(extract_ces, env_name, region, dry_run)
            for env_name in env_names
        ]
        for future in futures:
            ces = future.result()
            all_ces.extend([(ce, region) for ce in ces])

    if csv_filename:
        logger.info(f"Saving report to file: {csv_filename}")
        extracted_data = save_report_to_file(csv_filename)
        for username, bu in extracted_data:
            print(f"{username},{bu}")
    else:
        filename = f"ce_report_{'_'.join(sorted(env_names))}_{region}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.csv"
        logger.info(f"Saving report to file: {filename}")
        save_report_to_file(all_ces, filename)
        print(f"Report saved to {filename}")

    if dry_run:
        logger.info("Dry run: List of all CEs across the specified environments")
        for ce, region in all_ces:
            logger.info(
                f"Will be updating the expiration date for {ce} which is in ({region})"
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="List CEs across environments")
    parser.add_argument("--region", default=aws_region, help="AWS region to use")
    parser.add_argument(
        "--no-dry-run", help="if not provided dry run mode is on)", action="store_false"
    )
    parser.add_argument(
        "--env-names",
        nargs="*",
        default=EVERY_CE_ENV_NAMES,
        help="List of environment names to process",
    )
    parser.add_argument("--csv-file", help="Path to the CSV file to extract data from")

    args = parser.parse_args()
    aws_region = args.region

    if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

    main(dry_run=args.no_dry_run, env_names=args.env_names, csv_filename=args.csv_file)
