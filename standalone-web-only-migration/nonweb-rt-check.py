#!/usr/bin/env python3
import logging
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="cnx-routes-audit")


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

        accounts_filter = (
            Attr("internet-facing").eq(True)
            & Attr("network-web-only").eq(False)
            & Attr("network-type").eq("Connected-4-Tier-2-AZ")
            & Attr("network-ignore-update").ne(True)
            & Attr("status").eq("Active")
        )

        spoke_list = get_spokes(table_name, accounts_filter)
        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/CIP_INSPECTOR"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)
            check_cnx_routes(ec2_client, spoke, "private")
            if spoke.get("local_private_nat"):
                private_nat_gw_list = list_private_nat_gtws(ec2_client)
                check_cnx_routes(ec2_client, spoke, "local", private_nat_gw_list)

    except Exception as e:
        logger.error(e)


def list_private_nat_gtws(ec2_client):
    try:
        nat_gtws = ec2_client.describe_nat_gateways()["NatGateways"]
        private_nat_gw_list = []
        for nat_gtw in nat_gtws:
            if nat_gtw["ConnectivityType"] == "private":
                private_nat_gw_list.append(nat_gtw["NatGatewayId"])
        return private_nat_gw_list
    except Exception as e:
        logger.error(e)


def check_cnx_routes(ec2_client, spoke_info, rt_type, nat_gw_list=[]):
    try:
        default_routes = [
            "10.0.0.0/8",
            "15.163.150.0/24",
            "20.9.60.0/24",
            "63.247.112.0/20",
            "69.184.0.0/16",
            "75.96.208.0/20",
            "75.124.40.0/21",
            "85.132.3.210/32",
            "94.199.89.60/32",
            "94.199.92.200/32",
            "130.201.0.0/16",
            "138.241.0.0/16",
            "149.177.0.0/16",
            "149.178.0.0/15",
            "149.180.0.0/14",
            "149.184.0.0/13",
            "149.192.0.0/14",
            "149.196.0.0/16",
            "150.251.4.136/32",
            "150.251.4.144/32",
            "155.61.194.0/26",
            "155.61.194.64/26",
            "159.43.0.0/18",
            "159.43.87.32/27",
            "159.43.100.0/22",
            "159.43.168.0/24",
            "159.44.40.0/22",
            "159.44.111.0/24",
            "159.44.168.0/22",
            "159.220.192.0/20",
            "160.43.0.0/16",
            "161.99.0.0/16",
            "161.100.0.0/14",
            "164.63.0.0/16",
            "172.16.0.0/12",
            "192.101.110.0/24",
            "192.129.94.0/24",
            "192.152.41.0/24",
            "192.155.137.0/24",
            "192.155.138.0/24",
            "192.168.0.0/16",
            "192.195.167.0/24",
            "193.29.160.0/20",
            "193.36.173.0/24",
            "194.53.121.0/24",
            "194.127.154.0/23",
            "199.105.176.0/21",
            "199.105.184.0/23",
            "202.168.50.0/24",
            "203.118.240.0/24",
            "205.183.246.0/24",
            "208.134.161.0/24",
            "216.23.224.0/20",
            "216.221.208.0/20",
        ]

        additional_routes_dict = {
            "ap-southeast-1": [
                "158.224.34.0/23",
                "158.224.36.0/24",
                "158.224.70.0/24",
                "146.242.130.0/27",
                "146.242.134.0/27",
                "146.242.136.0/21",
            ],
            "ap-southeast-2": [
                "158.224.34.0/23",
                "158.224.36.0/24",
                "158.224.70.0/24",
                "146.242.130.0/27",
                "146.242.134.0/27",
                "146.242.136.0/21",
            ],
            "ap-southeast-3": [
                "158.224.34.0/23",
                "158.224.36.0/24",
                "158.224.70.0/24",
                "146.242.130.0/27",
                "146.242.134.0/27",
                "146.242.136.0/21",
            ],
            "eu-central-1": [
                "94.199.89.34/32",
                "94.199.90.104/30",
                "94.199.92.176/28",
                "159.43.97.0/24",
                "159.43.118.0/24",
            ],
            "eu-west-1": [
                "94.199.89.34/32",
                "94.199.90.104/30",
                "94.199.92.176/28",
                "159.43.97.0/24",
                "159.43.118.0/24",
            ],
            "us-east-1": [
                "159.43.90.0/24",
                "159.43.121.0/24",
                "159.44.104.0/22",
                "192.152.40.0/24",
            ],
            "us-east-2": [
                "159.43.90.0/24",
                "159.43.121.0/24",
                "159.44.104.0/22",
                "192.152.40.0/24",
            ],
        }
        exempt_routes = ["100.64.0.0/16", "0.0.0.0/0", spoke_info["ip-range"]]
        dest_cidr_blocks = (
            default_routes
            + additional_routes_dict.get(spoke_info["region"])
            + exempt_routes
        )

        route_tables = ec2_client.describe_route_tables(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        f"{rt_type}-subnet-routetable-*",
                    ],
                }
            ]
        )["RouteTables"]

        for route_table in route_tables:
            logger.info(
                f"Checking CNX routes from {rt_type} route table ({route_table['RouteTableId']}) from {spoke_info['account-name']} spoke account."
            )
            routes = list_rt_routes(ec2_client, route_table["RouteTableId"])
            for route in routes:
                if route not in dest_cidr_blocks:
                    logger.info(f"Route not on approved list: {route}")

    except Exception as e:
        logger.error(e)


def list_rt_routes(ec2_client, rt_id):
    """
    List RT Routes
    """
    try:
        response = ec2_client.describe_route_tables(
            RouteTableIds=[
                rt_id,
            ]
        )[
            "RouteTables"
        ][0]["Routes"]
        routes = [
            route["DestinationCidrBlock"]
            for route in response
            if route.get("DestinationCidrBlock")
        ]
        return routes
    except ClientError as client_error:
        logger.error("Error describing RT routes:")
        logger.error(client_error)
        raise Exception("Error describing RT routes.")


def delete_rt_route(ec2_client, dest_cidr_block, rt_id):
    """
    Delete RT Route
    """
    try:
        ec2_client.delete_route(
            DestinationCidrBlock=dest_cidr_block, RouteTableId=rt_id
        )
    except ClientError as client_error:
        logger.error("Error deleting RT route:")
        logger.error(client_error)


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
    logger.info(f"Count of accounts to be addressed: {count}")
    return result


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    args = parser.parse_args()
    main(args.hub_env)
