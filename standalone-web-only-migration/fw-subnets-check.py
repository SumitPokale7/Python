#!/usr/bin/env python3
import logging
import boto3
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="fw-subnets-check")


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


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        standalone_accounts_filter = (
            Attr("network-web-only").eq(True)
            & Attr("internet-facing").eq(True)
            & Attr("network-type").eq("Standalone-4-Tier-3-AZ")
            & Attr("status").eq("Active")
        )
        connected_accounts_filter = (
            Attr("internet-facing").eq(True)
            & Attr("network-web-only").eq(True)
            & Attr("network-type").eq("Connected-4-Tier-2-AZ")
            & Attr("status").eq("Active")
        )
        standalone_spokes = get_spokes(table_name, standalone_accounts_filter)
        connected_if_spokes = get_spokes(table_name, connected_accounts_filter)
        spoke_list = standalone_spokes + connected_if_spokes
        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/AWS_PLATFORM_ADMIN"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)
            describe_subnets = []
            describe_subnets = ec2_client.describe_subnets(
                Filters=[
                    {
                        "Name": "tag:Name",
                        "Values": [
                            "AWSFirewallManagerManagedResource",
                        ],
                    },
                ]
            )["Subnets"]
            if describe_subnets:
                logger.info(
                    f"Spoke {spoke['account-name']} ({spoke['account']}) has Firewall subnets present in {spoke['region']}"
                )

    except Exception as e:
        logger.error(e)


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
