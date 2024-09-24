#!/usr/bin/env python3
import logging
import boto3
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        connected_accounts_filter = (
            Attr("account-type").eq("Connected")
            & Attr("network-connected").not_exists()
            & Attr("status").eq("Active")
        )
        spoke_list = get_spokes(table_name, connected_accounts_filter)
        for spoke in spoke_list:
            set_spoke_field(
                spoke_name=spoke["account-name"],
                field_name="network-connected",
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


def get_spokes(table_name, filter):
    table = boto3.resource("dynamodb", region_name="eu-west-1").Table(table_name)

    params = {"TableName": table_name, "FilterExpression": filter}

    result = []
    count = 0
    while True:
        response = table.scan(**params)
        for item in response.get("Items", []):
            result.append(item)
            count = count + 1
        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )
    print(f"Count of accounts to be addressed: {count}")
    return result


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    args = parser.parse_args()
    main(args.hub_env)
