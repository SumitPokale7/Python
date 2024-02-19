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


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        accounts_filter = (
            Attr("internet-facing").eq(True)
            & Attr("network-web-only").eq(True)
            & Attr("network-type").eq("Connected-4-Tier-3-AZ")
            & Attr("status").eq("Active")
        )

        spoke_list = get_spokes(table_name, accounts_filter)
        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/AWS_PLATFORM_ADMIN"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)
            remove_cnx_routes(ec2_client, spoke, "private")
            if spoke.get("local_private_nat"):
                private_nat_gw_list = list_private_nat_gtws(ec2_client)
                remove_cnx_routes(ec2_client, spoke, "local", private_nat_gw_list)

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


def remove_cnx_routes(ec2_client, spoke_info, rt_type, nat_gw_list=[]):
    try:
        # Replace with tgw ids of H1/H2 environments if needed. Below are H3 values
        transit_gateway_id_dict = {
            "eu-west-1": "tgw-0787cce2851713313",
            "us-east-1": "tgw-0fd67d32ab317c33d",
            "us-east-2": "tgw-0a4e16d930bba15bd",
            "ap-southeast-1": "tgw-09ddc756aec980b44",
            "ap-southeast-2": "tgw-0bc3423a11ac8903b",
            "ap-southeast-3": "tgw-06ca5a544c86df12b",
        }

        default_routes = [
            "10.0.0.0/8",
            "194.127.154.0/23",
            "192.101.110.0/24",
            "192.129.94.0/24",
            "192.195.167.0/24",
            "193.36.173.0/24",
            "194.53.121.0/24",
            "203.118.240.0/24",
            "202.168.50.0/24",
            "149.178.0.0/15",
            "149.180.0.0/14",
            "149.184.0.0/13",
            "149.192.0.0/14",
            "149.196.0.0/16",
            "172.16.0.0/12",
            "193.29.160.0/20",
            "130.201.0.0/16",
            "138.241.0.0/16",
            "149.177.0.0/16",
            "161.99.0.0/16",
            "161.100.0.0/14",
            "164.63.0.0/16",
            "192.168.0.0/16",
            "69.184.0.0/16",
            "160.43.0.0/16",
            "199.105.176.0/21",
            "199.105.184.0/23",
            "205.183.246.0/24",
            "208.134.161.0/24",
            "159.43.0.0/18",
            "159.43.87.32/27",
            "155.61.194.0/26",
            "159.43.100.0/22",
            "159.43.168.0/24",
            "159.44.40.0/22",
            "159.44.111.0/24",
            "159.44.168.0/22",
            "159.220.192.0/20",
            "192.152.41.0/24",
            "192.155.137.0/24",
            "192.155.138.0/24",
            "63.247.112.0/20",
            "216.23.224.0/20",
            "216.221.208.0/20",
            "94.199.89.60/32",
            "94.199.92.200/32",
            "20.9.60.90/32",
            "20.9.60.107/32",
        ]

        additional_routes_dict = {
            "eu-west-1": [
                "159.43.97.0/24",
                "159.43.118.0/24",
                "85.132.3.210/32",
                "94.199.89.34/32",
                "94.199.90.104/30",
                "94.199.92.176/28",
            ],
            "us-east-1": ["155.61.194.64/26", "159.43.121.0/24"],
            "us-east-2": ["155.61.194.64/26", "159.43.121.0/24"],
            "ap-southeast-1": [
                "146.242.130.0/27",
                "146.242.134.0/27",
                "146.242.136.0/21",
            ],
            "ap-southeast-2": [],
            "ap-southeast-3": [],
            "eu-central-1": [
                "85.132.3.210/32",
                "94.199.89.34/32",
                "94.199.90.104/30",
                "94.199.92.176/28",
            ],
        }

        dest_cidr_blocks = default_routes + additional_routes_dict.get(
            spoke_info["region"]
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
            tgw_id = transit_gateway_id_dict.get(spoke_info["region"])
            rt_id = None
            for route in route_table["Routes"]:
                if (
                    route.get("DestinationCidrBlock") == "0.0.0.0/0"
                    and route.get("TransitGatewayId") == tgw_id
                ):
                    rt_id = route_table["RouteTableId"]
                elif (
                    route.get("DestinationCidrBlock") == "0.0.0.0/0"
                    and route.get("NatGatewayId") in nat_gw_list
                ):
                    rt_id = route_table["RouteTableId"]
            if rt_id:
                logger.info(
                    f"Removing CNX routes from {rt_type} route table ({rt_id}) from {spoke_info['account-name']} spoke account."
                )
                for route in route_table["Routes"]:
                    if route.get("DestinationCidrBlock") in dest_cidr_blocks:
                        delete_rt_route(
                            ec2_client, route["DestinationCidrBlock"], rt_id
                        )
            else:
                logger.info(
                    f"0.0.0.0/0 route is not pointing to the correct target in the {rt_type} route table {route_table['RouteTableId']} of {spoke_info['account-name']} spoke. Please investigate."
                )

    except Exception as e:
        logger.error(e)


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
