# -----------------------------------------------------------------
# resource_tagger.py
#
# This script processes the csv files generated as output from the process_enterprise.py script
# EX.
#   account_id,region,volume_id,tags
#   AccountName-B1,eu-west-1,vol-0acc7a4067af516b5,PROBLEM
# CSV file_name is passed as an input to the script
# Filter out results to only return resources without cloud-environment tag by modifying the extraction_utils.py
# EX. if "Tags" not in volume or not any(tag["Key"] == "cloud-environment" for tag in volume["Tags"])
# This script takes the resource volume_id or snapshot_id from the file and extracts CloudTrail "Create" event for the resource
# Extracted event is passed as an execution input to the resource_monitoring state machine to tag the resources
#
# -----------------------------------------------------------------

import boto3
import logging
import csv
import json
from botocore.exceptions import ClientError, ProfileNotFound
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Account mapping
accounts = {
    "AccountName-A1": "8373000000000",
    "WU2-A1": "0000000000000",
}


def extract_and_process_resources(csv_filename):
    """Extracts resources from a CSV file and processes them."""
    try:
        with open(csv_filename, mode="r", newline="") as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                account_id = row["account_id"]
                region = row["region"]
                resource_name = row.get("volume_id") or row.get("snapshot_id")
                process_resource(account_id, region, resource_name)
    except FileNotFoundError:
        logger.error(f"File {csv_filename} not found.")
    except Exception as e:
        logger.error(f"An error occurred while processing the CSV file: {e}")


def process_resource(account_id, region, resource_name):
    """Processes a single resource by looking up CloudTrail events and executing the state machine."""
    try:
        spoke_client = get_session(account_id, region).client("cloudtrail")
        result = lookup_cloudtrail_events(spoke_client, resource_name)
        if result:
            for item in result:
                cloudtrail_event = json.loads(item["CloudTrailEvent"])
                cloudtrail_event.pop("sessionCredentialFromConsole", None)
                formatted_result = format_event(item, cloudtrail_event)
                execution_input = json.dumps(formatted_result, indent=2)
                execute_resource_monitoring_state_machine(
                    account_id, region, execution_input
                )
        else:
            logger.info(f"No events found for resource {resource_name}")
    except ProfileNotFound:
        logger.error(f"Profile for account {account_id} not found.")
    except Exception as e:
        logger.error(
            f"An error occurred while processing resource {resource_name}: {e}"
        )


def get_session(account_id, region):
    """Generates a boto3 session for the specified account and region."""
    profile = f"{account_id}-role_DEVOPS"
    try:
        session = boto3.session.Session(profile_name=profile, region_name=region)
        logger.info(f"Using profile name: {profile}")
        return session
    except ProfileNotFound:
        logger.error(f"Profile {profile} not found.")
        raise


def lookup_cloudtrail_events(client, resource_name):
    """Looks up CloudTrail events for the specified resource."""
    try:
        response = client.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "ResourceName", "AttributeValue": resource_name},
            ],
        )
        return [
            event
            for event in response["Events"]
            if event["EventName"].startswith("Create")
            and resource_name.split("-")[0] in event["EventName"].lower()
        ]
    except ClientError as err:
        handle_client_error(err)
        return []
    except Exception as e:
        logger.error(f"An error occurred while looking up CloudTrail events: {e}")
        return []


def handle_client_error(err):
    """Handles ClientError exceptions."""
    error_code = err.response["Error"]["Code"]
    if error_code == "AccessDenied":
        logger.warning(f"Access denied: {err}")
    elif error_code == "InvalidClientTokenId":
        logger.error(f"Invalid client token ID: {err}")
    else:
        logger.error(f"ClientError: {err}")


def format_event(item, cloudtrail_event):
    """Formats the CloudTrail event into the required structure."""
    return {
        "version": "0",
        "id": item["EventId"],
        "detail-type": "AWS API Call via CloudTrail",
        "source": item["EventSource"],
        "account": cloudtrail_event["recipientAccountId"],
        "time": str(item["EventTime"]),
        "region": cloudtrail_event["awsRegion"],
        "resources": [],
        "detail": cloudtrail_event,
    }


def execute_resource_monitoring_state_machine(account_id, region, execution_input):
    """Executes the state machine with the extracted event as input."""
    try:
        _account_id = accounts[account_id]
        sf_client = get_session(account_id, region).client("stepfunctions")
        response = sf_client.start_execution(
            stateMachineArn=f"arn:aws:states:{region}:{_account_id}:stateMachine:Resource-Monitoring",
            input=execution_input,
        )
        logger.info(f"State machine execution started: {response}")
    except ClientError as err:
        handle_client_error(err)
    except Exception as e:
        logger.error(f"An error occurred while executing the state machine: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process a CSV file containing resource information."
    )
    parser.add_argument("csv_filename", type=str, help="The CSV file to be processed.")
    args = parser.parse_args()

    extract_and_process_resources(args.csv_filename)
