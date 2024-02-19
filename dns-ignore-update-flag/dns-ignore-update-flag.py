#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"
        # Update the list of spokes the flag should be added to
        spoke_list = []
        for spoke in spoke_list:
            set_spoke_field(
                spoke_name=spoke,
                field_name="dns_ignore_update",
                field_value=True,
                table_name=table_name,
            )

    except Exception as e:
        logger.error(e)


def set_spoke_field(spoke_name, field_name, field_value, table_name):
    logger.info(
        f"Updating {field_name}={field_value} for spoke {spoke_name} in Metadata table."
    )
    client = boto3.client("dynamodb", "eu-west-1")
    response = client.update_item(
        TableName=table_name,
        Key={"account-name": {"S": spoke_name}},
        UpdateExpression="SET #field=:value",
        ExpressionAttributeNames={"#field": field_name},
        ExpressionAttributeValues={":value": {"BOOL": field_value}},
        ReturnValues="ALL_NEW",
    )
    return response["Attributes"]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    args = parser.parse_args()
    main(args.hub_env)
