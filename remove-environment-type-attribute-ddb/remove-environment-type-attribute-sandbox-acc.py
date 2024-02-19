#!/usr/bin/env python3
import logging
import boto3
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser


# Create a logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


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
    logger.info(f"Total Sandbox accounts: {count}")
    return result


def delete_environment_type_attribute(spoke_name, table_name):
    logger.info(
        f"Removing environment-type attribute for spoke {spoke_name} from Dynamo DB metadata table."
    )

    client = boto3.client("dynamodb", "eu-west-1")
    client.update_item(
        TableName=table_name,
        Key={"account-name": {"S": spoke_name}},
        UpdateExpression="REMOVE #field",
        ExpressionAttributeNames={"#field": "environment-type"},
    )


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        sandbox_accounts_filter = Attr("account-type").eq("Sandbox")
        spoke_list = get_spokes(table_name, sandbox_accounts_filter)
        for spoke in spoke_list:
            if "environment-type" in spoke:
                delete_environment_type_attribute(
                    spoke_name=spoke["account-name"], table_name=table_name
                )
            else:
                logger.info(
                    "No Sandbox account found with environment-type attribute."
                )

    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    args = parser.parse_args()
    main(args.hub_env)
