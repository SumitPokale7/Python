#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser
import json

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def main(hub_env, hub_account_id):
    try:
        # Update the spoke list with the accounts you want to migrate
        spoke_list = []
        for spoke in spoke_list:
            spoke_info = set_spoke_field(
                spoke_name=spoke,
                hub_env=hub_env,
                field_name="network-type",
                field_value="Connected-4-Tier-3-AZ",
            )
            update_spoke(hub_env, hub_account_id, spoke, spoke_info["account"]["S"])

    except Exception as e:
        logger.error(e)


def set_spoke_field(spoke_name, hub_env, field_name, field_value):
    table_name = f"{hub_env}-DYN_METADATA"
    client = boto3.client("dynamodb", "eu-west-1")
    logger.info(
        f"Updating {field_name}={field_value} for spoke {spoke_name} in Metadata table."
    )
    response = client.update_item(
        TableName=table_name,
        Key={"account-name": {"S": spoke_name}},
        UpdateExpression="SET #field=:value",
        ExpressionAttributeNames={"#field": field_name},
        ExpressionAttributeValues={":value": {"S": field_value}},
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


def update_spoke(hub_env, hub_account_id, spoke_name, spoke_account_id):
    client = boto3.client("lambda", region_name="eu-west-1")
    lambda_name = f"{hub_env}-LMD_SPOKE-NETWORK-PROVISIONER-Custom_Resource_Handler"
    payload = {
        "ResourceType": "Custom::SpokeVpc",
        "RequestType": "Update",
        "StackId": "FakeStackId",
        "RequestId": "FakeRequestId",
        "LogicalResourceId": "FakeLogicalResourceId",
        "PhysicalResourceId": "FakePhysicalResourceId",
        "ResourceProperties": {
            "AccountName": spoke_name,
            "AccountId": spoke_account_id,
            "ServiceToken": f"arn:aws:lambda:eu-west-1:{hub_account_id}:function:{hub_env}-LMD_SPOKE-NETWORK-PROVISIONER-Custom_Resource_Handler",
        },
    }
    logger.info(f"Triggering NETWORK-STACK Update for {spoke_name} account.")
    client.invoke(
        FunctionName=lambda_name,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    parser.add_argument("hub_account_id", type=str)
    args = parser.parse_args()
    main(args.hub_env, args.hub_account_id)
