#!/usr/bin/env python3
import logging
import boto3
import json
import os
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


# Set logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_session(aws_profile):
    """Creates a BOTO3 session using credentials."""
    return boto3.Session(profile_name=aws_profile)


def get_account_ids(metadata_table, env_type, region):
    logger.info("Scanning over DDB table: " + metadata_table.table_name)

    filter_expression = (
        Attr("status").eq("Active")
        & Attr("account-type").eq("Connected")
        & Attr("region").eq(region)
        & Attr("environment-type").eq(env_type)
    )

    params = {"FilterExpression": filter_expression, "ProjectionExpression": "account"}
    result = []

    while True:
        response = metadata_table.scan(**params)

        for item in response.get("Items", []):
            result.append(item)

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )

    return [account["account"] for account in result]


def main(batch_size, env_type, region, hub_name, aws_profile):
    metadata_table_name = f"{hub_name}-DYN_METADATA"

    logger.info(
        f"Creating batches of size {batch_size} from table {metadata_table_name} with env-type {env_type}"
    )

    session = create_session(aws_profile)

    metadata_table = session.resource("dynamodb", region_name="eu-west-1").Table(
        metadata_table_name
    )

    accounts = get_account_ids(metadata_table, env_type, region)

    logger.info(
        f"Found {len(accounts)} accounts. Putting in to batches of {batch_size}"
    )

    batches = [
        accounts[x: x + batch_size] for x in range(0, len(accounts), batch_size)
    ]

    for i in range(0, len(batches)):
        print(f"Batch: {i}\n" f"{json.dumps(batches[i])}\n")


if __name__ == "__main__":
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-s", "--size", type=int, help="Size of batches to generate", default=50
    )
    parser.add_argument(
        "-e",
        "--env",
        type=str,
        help="Environment type value to use in scan",
        default="NonProd",
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        help="Region value to use in scan",
        default="eu-west-1",
    )
    parser.add_argument(
        "-n", "--name", type=str, help="Hub account name", default="WH-0003"
    )
    parser.add_argument(
        "-p",
        "--profile",
        type=str,
        help="Hub account name",
        default=os.environ.get("AWS_DEFAULT_PROFILE"),
    )
    args = parser.parse_args()

    main(args.size, args.env, args.region, args.name, args.profile)
