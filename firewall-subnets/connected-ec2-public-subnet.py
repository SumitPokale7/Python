#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="public-subnets-connected-accounts"
    )


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


def main(environment_type):
    try:
        list_accounts = get_connected_spokes(environment_type)
        public_subnet_instances = {}

        for account in list_accounts:
            subnet_list_in_account = set()
            account_number = account["account"]["S"]
            role = f"arn:aws:iam::{account_number}:role/CIP_MANAGER"
            region = account["region"]["S"]

            client_ec2 = create_client("ec2", role, region)
            describe_public_subnets = client_ec2.describe_subnets(
                Filters=[
                    {
                        "Name": "tag:Name",
                        "Values": [
                            "public-subnet-*",
                        ],
                    },
                ]
            )
            for subnet in describe_public_subnets["Subnets"]:
                subnet_list_in_account.add(subnet["SubnetId"])

            describe_instances = client_ec2.describe_instances()
            # check for instance id
            instance_ids = []
            for instance in describe_instances["Reservations"]:
                for image in instance["Instances"]:
                    if image["SubnetId"] in subnet_list_in_account:
                        instance_ids.append(image["InstanceId"])
            public_subnet_instances[account_number] = instance_ids
        for key, value in public_subnet_instances.items():
            print(f"EC2 instances deployed in the public subnets : {key, value}")
    except Exception as e:
        logging.error(e)


def get_connected_spokes(environment_type):
    table_name = "WH-0003-DYN_METADATA"
    # can replace the network type accordingly : Connected-4-Tier-2-AZ and Standalone-4-Tier-3-AZ
    params = {
        "TableName": table_name,
        "FilterExpression": "#s = :active AND #nt = :networktype AND (#if = :internetfacing OR #if = :ifstr) AND #env = :environment",
        "Select": "SPECIFIC_ATTRIBUTES",
        "ProjectionExpression": "#c, account, #nt, #if",
        "ExpressionAttributeNames": {
            "#c": "region",
            "#s": "status",
            "#nt": "network-type",
            "#if": "internet-facing",
            "#env": "environment-type",
        },
        "ExpressionAttributeValues": {
            ":active": {"S": "Active"},
            ":networktype": {"S": "Connected-4-Tier-2-AZ"},
            ":internetfacing": {"BOOL": True},
            ":ifstr": {"S": "true"},
            ":environment": {"S": environment_type},
        },
    }

    result = []
    client = boto3.client("dynamodb", "eu-west-1")
    count = 0
    while True:
        response = client.scan(**params)
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
    parser.add_argument("environment_type", type=str)
    args = parser.parse_args()
    main(args.environment_type)
