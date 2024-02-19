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


def get_active_accounts(metadata_table):
    logger.info("Scanning over DDB table: " + metadata_table.table_name)

    filter_expression = (
        Attr("status").eq("Active")
        & Attr("managed-by-control-tower").not_exists()
        & Attr("account-type").ne("Hub")
    )

    params = {"FilterExpression": filter_expression}
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

    return result


def main(hub_name, aws_profile, batch_size=10):
    metadata_table_name = f"{hub_name}-DYN_METADATA"

    logger.info(
        f"Creating batches of size {batch_size} from table {metadata_table_name}"
    )

    session = create_session(aws_profile)

    metadata_table = session.resource("dynamodb", region_name="eu-west-1").Table(
        metadata_table_name
    )

    accounts = get_active_accounts(metadata_table)

    logger.info(
        f"Found {len(accounts)} accounts. Putting in to batches of {batch_size}"
    )

    account_metadata = []
    for account in accounts:
        account_metadata.append(
            {
                'account': account['account'],
                'account-name': account['account-name']
            }
        )
    batches = [
        account_metadata[x: x + batch_size]
        for x in range(0, len(accounts), batch_size)
    ]
    for i in range(0, len(batches)):
        print(f"Batch: {i}\n" f"{json.dumps(batches[i])}\n")


if __name__ == "__main__":
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n", "--name", type=str, help="Hub account name", required=True)
    parser.add_argument("-p", "--profile", type=str, help="aws cli profile", default=os.environ.get("AWS_DEFAULT_PROFILE"))
    parser.add_argument("-s", "--size", type=int, help="Size of batches", default=10)
    args = parser.parse_args()

    main(args.name, args.profile, args.size)
