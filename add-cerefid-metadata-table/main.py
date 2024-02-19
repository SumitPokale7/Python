#!/usr/bin/env python3
import boto3
import csv
import logging
from argparse import ArgumentParser

logging.basicConfig(level=logging.INFO)


def read_csv(filename):
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row


def update_dynamodb_item(table, key, value):
    response = table.update_item(
        Key={"account-name": key},
        UpdateExpression="set #n = if_not_exists(#n, :val)",
        ExpressionAttributeNames={"#n": "CERefID"},
        ExpressionAttributeValues={":val": value},
        ReturnValues="UPDATED_NEW",
    )
    return response


def get_dynamodb_item(table, key):
    response = table.get_item(Key={"account-name": key})
    return response["Item"]


def main(path, table, dry_run):
    dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
    table = dynamodb.Table(table)
    update, no_update = 0, 0
    for row in read_csv(path):
        if row["CE AD Name"]:
            logging.info(f"Updating {row['CE AD Name']} for {row['Name']}")
            if not dry_run:
                try:
                    result = update_dynamodb_item(table, row["Name"], row["CE AD Name"])
                    logging.info(f"Updated {row['Name']} with {row['CE AD Name']}")
                    logging.debug(f"Updated {result}")
                    continue
                except Exception as e:
                    logging.error(f"Failed to update {row['Name']}: {e}")
                    continue

            logging.info("Dry run, skipping update")
            try:
                result = get_dynamodb_item(table, row["Name"])
                if result.get("CERefID", None):
                    logging.info(f"CERefID exists wont update\n{row['Name']}")
                    logging.debug(f"{result}")
                    no_update += 1
                else:
                    result.update({"CERefID": row["CE AD Name"]})
                    logging.info(f"CERefID didnt exist so adding\n{row['Name']}")
                    logging.debug(f"{result}")
                    update += 1
            except Exception as e:
                logging.error(f"Failed to get {row['Name']}: {e}")

    if dry_run:
        logging.info(f"Records to be updated: {update} / {table.item_count}")
        logging.info(f"Records to remain unchanged: {no_update} / {table.item_count}")
        logging.info("Note, table count may be out of date, doesnt perform scan")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file_path", type=str, help="CSV file path", required=True
    )
    parser.add_argument(
        "-t", "--table", type=str, help="DynamoDB Table name", required=True
    )
    parser.add_argument("--no-dry-run", help="Dry run", action="store_false")
    args = parser.parse_args()
    logging.info(args.no_dry_run)
    main(args.file_path, args.table, args.no_dry_run)
