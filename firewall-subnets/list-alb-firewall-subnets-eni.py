#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="firewall-subnets")


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


def main(network_type, environment_type):
    try:
        list_accounts = get_connected_spokes(network_type, environment_type)
        common_subnet_dict = {}
        common_eni_dict = {}
        for account in list_accounts:
            account_number = account["account"]["S"]
            role = f"arn:aws:iam::{account_number}:role/CIP_MANAGER"
            region = account["region"]["S"]
            subnet_list_in_account = set()
            # creating client for ec2 to describe firewall subnets
            client_ec2 = create_client("ec2", role, region)
            describe_subnets = client_ec2.describe_subnets(
                Filters=[
                    {
                        "Name": "tag:Name",
                        "Values": [
                            "AWSFirewallManagerManagedResource",
                        ],
                    },
                ]
            )
            for subnet in describe_subnets["Subnets"]:
                subnet_list_in_account.add(subnet["SubnetId"])
            # create client for elbv2, replace the below service to "elb" for elbv1 and "elbv2" for elbv2
            client_elb = create_client("elbv2", role, region)
            describe_elb = client_elb.describe_load_balancers()
            common_subnet_list = set()
            # 1. AWS Load Balancers deployed in the Firewall subnets
            for elb in describe_elb["LoadBalancers"]:
                for lb in elb["AvailabilityZones"]:
                    if lb["SubnetId"] in subnet_list_in_account:
                        common_subnet_list.add(lb["SubnetId"])
            # inserting into dict to avoid multiple stats
            if len(common_subnet_list) != 0:
                common_subnet_dict[account_number] = common_subnet_list

            # 2. existing ENIs deployed in the Firewall subnets
            describe_network_interfaces = client_ec2.describe_network_interfaces()
            common_eni_list = set()
            for eni in describe_network_interfaces["NetworkInterfaces"]:
                if eni["SubnetId"] in subnet_list_in_account:
                    common_eni_list.add(eni["NetworkInterfaceId"])
            if len(common_eni_list) != 0:
                common_eni_dict[account_number] = common_eni_list

        # pretty printing
        for key, value in common_subnet_dict.items():
            print(
                f"AWS Load Balancers deployed in the Firewall subnets : {key, value} "
            )

        for key, value in common_eni_dict.items():
            print(f"Existing ENI deployed in Firewall Subnets : {key, value}")

    except Exception as e:
        logging.error(e)


def get_connected_spokes(network_type, environment_type):
    table_name = "WH-0003-DYN_METADATA"
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
            ":networktype": {"S": network_type},
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
    network_type = ["Connected-4-Tier-2-AZ", "Standalone-4-Tier-3-AZ"]
    for network in network_type:
        main(network, args.environment_type)
