#!/usr/bin/env python3
import os
import sys
from typing import Any, Generator, Tuple, List

import boto3

METADATA_PK_NAME = "account-name"
METADATA_TABLE_NAME = "DYN_METADATA"
DRY_RUN = False


def usage():
    print(f"Usage: ./{os.path.basename(__file__)} <params>")
    print()
    print("Parameters:")
    print("    -h, --help       - display help")
    print("    -n, --dry-run    - execute without real action")
    print()
    print("Environment variables:")
    print(
        "    ACCOUNT_PREFIX=WH-0000           - Account prefix as part of naming convention"
    )
    print("    AWS_PROFILE=WH-0000-role_DEVOPS  - AWS profile to use")
    print("    AWS_REGION=eu-west-1             - AWS region to run")
    print()
    print("Notes:")
    print(
        "    - value in ACCOUNT_PREFIX might differ from the role prefix (eg, H1/H2/H3)"
    )
    print()


def value_mapping() -> Generator[Tuple[str, str, bool], None, None]:
    yield ("internet-facing", "Yes", True)
    yield ("internet-facing", "No", False)


def load_old_items(table, field_name: str, old_val: Any) -> Generator[dict, None, None]:
    params = {
        "FilterExpression": "#F = :OV",
        "ProjectionExpression": "#PK, #F",
        "ExpressionAttributeNames": {
            "#PK": METADATA_PK_NAME,
            "#F": field_name,
        },
        "ExpressionAttributeValues": {
            ":OV": old_val,
        },
    }

    while True:
        response = table.scan(**params)

        for item in response.get("Items", []):
            yield item

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )


def update_item(item: dict, table, field_name: str, old_val: Any, new_val: Any) -> str:
    if DRY_RUN:
        print(
            f"dry-run: about to update_item({item[METADATA_PK_NAME]!r}, {field_name!r}, {old_val!r}, {new_val!r}) ..."
        )
        return item[METADATA_PK_NAME]

    try:
        table.update_item(
            Key={METADATA_PK_NAME: item[METADATA_PK_NAME]},
            UpdateExpression="SET #F = :NV",
            ConditionExpression="#F = :OV",
            ExpressionAttributeNames={
                "#F": field_name,
            },
            ExpressionAttributeValues={
                ":OV": old_val,
                ":NV": new_val,
            },
            ReturnValues="UPDATED_NEW",
        )
    except Exception as e:
        raise e
    else:
        return item[METADATA_PK_NAME]


def migrate_ddb_schema(
    dynamodb, table_name: str, field_name: str, old_val: Any, new_val: Any
) -> List[dict]:
    table = dynamodb.Table(table_name)

    result = []

    for item in load_old_items(table, field_name, old_val):
        result.append(update_item(item, table, field_name, old_val, new_val))

    return result


def main():
    if any([v.lower() in ["-h", "--help"] for v in sys.argv]):
        usage()
        exit(0)

    global DRY_RUN
    DRY_RUN = any([v.lower() in ["-n", "--dry-run"] for v in sys.argv])

    account_prefix = os.getenv("ACCOUNT_PREFIX", "").strip()
    aws_profile = os.getenv("AWS_PROFILE", "").strip()
    aws_region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "")).strip()

    if not account_prefix or not aws_profile or not aws_region:
        print("Error: missing required environment variables.")
        usage()
        exit(1)

    print("Starting ...")

    table_name = f"{account_prefix}-{METADATA_TABLE_NAME}"

    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    account_id = session.client("sts").get_caller_identity()["Account"]

    dynamodb = session.resource("dynamodb")

    print()
    print(
        f"Schema migration{' [DRY-RUN]' if DRY_RUN else ''} on DDB {table_name!r} table in {account_prefix} ({account_id}) account."
    )
    print()

    for field_name, old_val, new_val in value_mapping():
        print(
            f" - {field_name}: {type(old_val).__name__}({old_val!r}) => {type(new_val).__name__}({new_val!r})"
        )

    print()
    input("Proceed? <Ctrl-C> to abort ... ")
    print()

    for field_name, old_val, new_val in value_mapping():
        print(
            f"Migrating {field_name!r} field from {type(old_val).__name__}({old_val!r}) to {type(new_val).__name__}({new_val!r}) ..."
        )

        items = migrate_ddb_schema(dynamodb, table_name, field_name, old_val, new_val)

        if not items:
            print("everything is up-2-date")
        else:
            print(f"changed {len(items)} item(s):")
            tmp = "\n - ".join(items)
            print(f" - {tmp}")

        print()

    print("DONE")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Aborted, bye.")
        exit(130)
