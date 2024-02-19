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
    return sts_client.assume_role(RoleArn=role, RoleSessionName="public-nacl-audit")


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


def main(hub_env, network_type):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        # network-type can be Connected-4-Tier-3-AZ, Connected-4-Tier-2-AZ or Standalone-4-Tier-3-AZ
        accounts_filter = (
            Attr("internet-facing").eq(True)
            & Attr("network-web-only").eq(True)
            & Attr("network-type").eq(network_type)
            & Attr("status").eq("Active")
        )

        source_ip = {
            "Standalone-4-Tier-3-AZ": "0.0.0.0/0",
            "Connected-4-Tier-2-AZ": "10.0.0.0/8",
            "Connected-4-Tier-3-AZ": "10.0.0.0/8",
        }

        spoke_list = get_spokes(table_name, accounts_filter)
        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/CIP_INSPECTOR"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)

            allowed_nacl_rules = [
                {
                    "CidrBlock": spoke["ip-range"],
                    "Egress": True,
                    "Protocol": "-1",
                    "RuleAction": "allow",
                    "RuleNumber": 100,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "PortRange": {"From": 80, "To": 80},
                    "Protocol": "6",
                    "RuleAction": "allow",
                    "RuleNumber": 200,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "PortRange": {"From": 443, "To": 443},
                    "Protocol": "6",
                    "RuleAction": "allow",
                    "RuleNumber": 300,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "PortRange": {"From": 1024, "To": 65535},
                    "Protocol": "6",
                    "RuleAction": "allow",
                    "RuleNumber": 400,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "Protocol": "-1",
                    "RuleAction": "deny",
                    "RuleNumber": 32767,
                },
                {
                    "CidrBlock": spoke["ip-range"],
                    "Egress": False,
                    "Protocol": "-1",
                    "RuleAction": "allow",
                    "RuleNumber": 100,
                },
                {
                    "CidrBlock": source_ip[network_type],
                    "Egress": False,
                    "PortRange": {"From": 1024, "To": 65535},
                    "Protocol": "6",
                    "RuleAction": "allow",
                    "RuleNumber": 200,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "PortRange": {"From": 443, "To": 443},
                    "Protocol": "6",
                    "RuleAction": "allow",
                    "RuleNumber": 300,
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "Protocol": "-1",
                    "RuleAction": "deny",
                    "RuleNumber": 32767,
                },
            ]

            nacl_entries = ec2_client.describe_network_acls(
                Filters=[
                    {
                        "Name": "tag:Name",
                        "Values": [
                            "public-subnet-nacl",
                        ],
                    },
                ]
            )["NetworkAcls"][0]["Entries"]

            print(
                f"Non-compliant public nacl rules for {spoke['account-name']}({account_number})"
            )
            for nacl_rule in nacl_entries:
                if nacl_rule not in allowed_nacl_rules:
                    print(nacl_rule)

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
    parser.add_argument("network_type", type=str)
    args = parser.parse_args()
    main(args.hub_env, args.network_type)
