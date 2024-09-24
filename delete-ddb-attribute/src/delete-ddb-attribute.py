import logging
import os
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ENVIRONMENT = os.environ.get("Environment")
TABLE_NAME = f"WH-{ENVIRONMENT}-DYN_METADATA"

dynamodb_resource = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")


def lambda_handler(event, context):
    try:
        attribute_to_remove = event.get("attribute_to_remove")
        if not attribute_to_remove:
            raise ValueError('Missing "attribute_to_remove" in the event payload')
        logger.info(f'Starting to remove "{attribute_to_remove}" from all active accounts')
        active_accounts = get_active_accounts(attribute_to_remove)
        if active_accounts:
            logger.info(f"Found {len(active_accounts)} active accounts")
            for account in active_accounts:
                remove_attribute(account["account-name"], attribute_to_remove)
            return
        else:
            logger.info("No active accounts found with the specified attribute")
            return
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return


def get_active_accounts(attribute_to_remove):
    table = dynamodb_resource.Table(TABLE_NAME)

    active_accounts_filter = Attr("status").eq("Active") & Attr(attribute_to_remove).exists()

    active_accounts = []
    response = table.scan(FilterExpression=active_accounts_filter)
    active_accounts.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=active_accounts_filter,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        active_accounts.extend(response.get("Items", []))

    return active_accounts


def remove_attribute(account_name, attribute_to_remove):
    try:
        # Fetch the item to check if the attribute exists
        response = dynamodb_client.get_item(
            TableName=TABLE_NAME, Key={"account-name": {"S": account_name}}
        )
        item = response.get("Item")
        if item and attribute_to_remove in item:
            dynamodb_client.update_item(
                TableName=TABLE_NAME,
                Key={"account-name": {"S": account_name}},
                UpdateExpression="REMOVE #attr",
                ExpressionAttributeNames={"#attr": attribute_to_remove},
            )
            logger.info(
                f'Removed "{attribute_to_remove}" from account "{account_name}"'
            )
        else:
            logger.info(
                f'Attribute "{attribute_to_remove}" not found in account "{account_name}"'
            )
            return
    except ClientError as e:
        logger.error(f"Failed to remove attribute: {str(e)}", exc_info=True)
        raise e
