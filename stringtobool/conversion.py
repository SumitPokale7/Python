#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser
from typing import Any

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="stringtobool")


def create_client(service, role, region):
    """Creates a BOTO3 client using the correct target accounts Role."""
    creds = create_creds(role, region)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name=region,
    )
    return client


def cast_bool(value: Any) -> bool:
    return str(value).lower() in ("on", "yes", "true", "1")


def main(hub_env):
    table_name = f"WH-{hub_env}-DYN_METADATA"
    params = {
        "TableName": table_name,
        "FilterExpression": "#s = :active",
        "Select": "SPECIFIC_ATTRIBUTES",
        "ProjectionExpression": "account,#if,#accname",
        "ExpressionAttributeNames": {
            "#s": "status",
            "#if": "internet-facing",
            "#accname": "account-name",
        },
        "ExpressionAttributeValues": {":active": {"S": "Active"}},
    }

    client = boto3.client("dynamodb", "eu-west-1")
    count = 0
    while True:
        response = client.scan(**params)
        for item in response.get("Items", []):
            account_name = item["account-name"]["S"]
            print(item)
            if "internet-facing" in item and "S" in item["internet-facing"]:
                count += 1
                update_params = {
                    "TableName": table_name,
                    "Key": {"account-name": {"S": account_name}},
                    "UpdateExpression": "SET #if = :val",
                    "ExpressionAttributeNames": {"#if": "internet-facing"},
                    "ExpressionAttributeValues": {
                        ":val": {"BOOL": cast_bool(item["internet-facing"]["S"])}
                    },
                }

                client.update_item(**update_params)

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )
    print(f"Count of accounts to be addressed: {count}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str, required=True)
    args = parser.parse_args()
    main(args.hub_env)
