#!/usr/bin/env python3
import logging
import boto3
import time
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="public-nacl-update")


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
            Attr("status").eq("Active")
            & Attr("date_first_user_added_to_operations_ad_group").exists()
            & Attr("account-type").ne("Foundation")
        )

        spoke_list = get_spokes(table_name, accounts_filter)

        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/AWS_PLATFORM_ADMIN"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)
            cfn_client = create_client("cloudformation", role, region)
            logger.info(f"Checking spoke {spoke['account-name']} compliance.")
            check_drift = check_drift_detection(cfn_client, spoke["account-name"])
            if check_drift["StackDriftStatus"] != "IN_SYNC":
                logger.info(
                    f"{spoke['account-name']}-NETWORK-STACK drift status: {check_drift['StackDriftStatus']}. Check account for more information."
                )
            logger.info(f"Checking spoke {spoke['account-name']} route tables.")
            vpc_default_routes = [
                {
                    "DestinationCidrBlock": spoke["ip-range"],
                    "GatewayId": "local",
                    "Origin": "CreateRouteTable",
                    "State": "active",
                },
                {
                    "DestinationCidrBlock": "100.64.0.0/16",
                    "GatewayId": "local",
                    "Origin": "CreateRouteTable",
                    "State": "active",
                },
            ]
            if spoke["account-type"] == "Connected":
                check_connected_rts(ec2_client, cfn_client, spoke, vpc_default_routes)
            elif spoke["account-type"] == "Standalone":
                check_standalone_rts(ec2_client, cfn_client, spoke, vpc_default_routes)
    except Exception as e:
        logger.error(e)


def check_connected_rts(ec2_client, cfn_client, spoke, vpc_default_routes):
    try:
        local_rts = get_route_tables(ec2_client, "local-subnet-routetable-*")
        private_rts = get_route_tables(ec2_client, "private-subnet-routetable-*")

        if spoke["network-type"] == "Connected-4-Tier-2-AZ":
            if spoke.get("internet-facing") is True:
                firewall_rts = get_route_tables(
                    ec2_client, "AWSFirewallManagerManagedResource"
                )
                for firewall_rt in firewall_rts:
                    for route in firewall_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("GatewayId").startswith(
                                "igw-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {firewall_rt['RouteTableId']} firewall route table"
                                )
                public_rts = get_route_tables(ec2_client, "public-subnet-routetable-*")
                for public_rt in public_rts:
                    for route in public_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if (
                                route.get("DestinationCidrBlock") == "0.0.0.0/0"
                                and route.get("GatewayId").startswith("vpce-")
                            ) or (
                                route.get("DestinationCidrBlock") == "10.0.0.0/8"
                                and route.get("TransitGatewayId").startswith("tgw-")
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} public route table"
                                )
                igw_rt = get_route_tables(ec2_client, "IGW-routetable")
                cidr = spoke["ip-range"][:-4]
                public_subnets_cidrs = [cidr + "128/27", cidr + "160/27"]
                for route in igw_rt[0]["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) in public_subnets_cidrs and route.get("GatewayId").startswith(
                            "vpce-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} IGW route table"
                            )

                # Private CNX RT check
                check_cnx_routes(spoke, private_rts)
                # Local CNX RT check
                check_cnx_routes(spoke, local_rts)
            else:
                for private_rt in private_rts:
                    for route in private_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get(
                                "TransitGatewayId"
                            ).startswith(
                                "tgw-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {private_rt['RouteTableId']} private route table"
                                )

                for local_rt in local_rts:
                    for route in local_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                                "nat-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {local_rt['RouteTableId']} local route table"
                                )

        elif spoke["network-type"] == "Connected-4-Tier-3-AZ":
            public_rts = get_route_tables(ec2_client, "public-subnet-routetable-*")
            if spoke.get("internet-facing") is True:
                for public_rt in public_rts:
                    for route in public_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if (
                                route.get("DestinationCidrBlock") == "0.0.0.0/0"
                                and route.get("GatewayId").startswith("igw-")
                            ) or (
                                route.get("DestinationCidrBlock") == "10.0.0.0/8"
                                and route.get("TransitGatewayId").startswith("tgw-")
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} public route table"
                                )
            for private_rt in private_rts:
                for route in private_rt["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("TransitGatewayId").startswith(
                            "tgw-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {private_rt['RouteTableId']} private route table"
                            )

            for local_rt in local_rts:
                for route in local_rt["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                            "nat-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {local_rt['RouteTableId']} local route table"
                            )

        elif spoke["network-type"] == "ConnectedTGW-1-Tier-3-AZ-Private":
            spoke_name = spoke["account-name"]
            response = cfn_client.describe_stacks(
                StackName=f"{spoke_name}-NETWORK-STACK"
            )
            outputs = response["Stacks"][0]["Outputs"]
            for output in outputs:
                keyName = output["OutputKey"]
                if keyName == "PrivateRoutingTables":
                    private_rts = output["OutputValue"].split(",")
            for private_rt in private_rts:
                routes = get_routes(ec2_client, private_rt)
                for route in routes:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("TransitGatewayId").startswith(
                            "tgw-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {private_rt} private route table"
                            )
            for local_rt in local_rts:
                for route in local_rt["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                            "nat-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {local_rt['RouteTableId']} local route table"
                            )

    except Exception as e:
        logger.error("Error checking route tables for the account:")
        logger.error(e)
        raise Exception("Error checking route tables for the account.")


def check_standalone_rts(ec2_client, cfn_client, spoke, vpc_default_routes):
    try:
        local_rts = get_route_tables(ec2_client, "local-subnet-routetable-*")
        private_rts = get_route_tables(ec2_client, "private-subnet-routetable-*")
        public_rts = get_route_tables(ec2_client, "public-subnet-routetable-*")
        if spoke["network-type"] == "Standalone-4-Tier-3-AZ":
            if spoke.get("network-web-only") is True:
                for public_rt in public_rts:
                    for route in public_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("GatewayId").startswith(
                                "igw-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} public route table"
                                )
            else:
                for public_rt in public_rts:
                    for route in public_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("GatewayId").startswith(
                                "vpce-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} public route table"
                                )

                firewall_rts = get_route_tables(
                    ec2_client, "AWSFirewallManagerManagedResource"
                )
                for firewall_rt in firewall_rts:
                    for route in firewall_rt["Routes"]:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("GatewayId").startswith(
                                "igw-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {firewall_rt['RouteTableId']} firewall route table"
                                )

                igw_rt = get_route_tables(ec2_client, "IGW-routetable")
                cidr = spoke["ip-range"][:-6]
                public_subnets_cidrs = [
                    cidr + "32.0/21",
                    cidr + "40.0/21",
                    cidr + "48.0/21",
                ]
                for route in igw_rt[0]["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) in public_subnets_cidrs and route.get("GatewayId").startswith(
                            "vpce-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {public_rt['RouteTableId']} IGW route table"
                            )
            for private_rt in private_rts:
                for route in private_rt["Routes"]:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                            "nat-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {private_rt['RouteTableId']} private route table"
                            )
            for local_rt in local_rts:
                for route in local_rt["Routes"]:
                    if route not in vpc_default_routes:
                        print(
                            f"Route {route} is not matching the expected architecture in {local_rt['RouteTableId']} local route table"
                        )

        if spoke["network-type"] == "StandaloneV3-3-Tier-3-AZ-Public-External-Private":
            spoke_name = spoke["account-name"]
            outputs = cfn_client.describe_stacks(
                StackName=f"{spoke_name}-NETWORK-STACK"
            )["Stacks"][0]["Outputs"]
            stack_outputs = {
                output["OutputKey"]: output["OutputValue"] for output in outputs
            }
            public_rt = stack_outputs["PublicRoutingTable"]
            public_routes = get_routes(ec2_client, public_rt)
            private_rts = [
                stack_outputs["PrivateRoutingTableA"],
                stack_outputs["PrivateRoutingTableB"],
                stack_outputs["PrivateRoutingTableC"],
            ]
            for route in public_routes:
                if route not in vpc_default_routes:
                    if route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get(
                        "GatewayId"
                    ).startswith("igw-"):
                        pass
                    else:
                        print(
                            f"Route {route} is not matching the expected architecture in {public_rt} public route table"
                        )
            for private_rt in private_rts:
                routes = get_routes(ec2_client, private_rt)
                for route in routes:
                    if route not in vpc_default_routes:
                        if route.get(
                            "DestinationCidrBlock"
                        ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                            "nat-"
                        ):
                            pass
                        else:
                            print(
                                f"Route {route} is not matching the expected architecture in {private_rt} private route table"
                            )
            if spoke.get("internet-facing") is True:
                external_rts_ids = [
                    "ExternalRoutingTableA",
                    "ExternalRoutingTableB",
                    "ExternalRoutingTableC",
                ]
                external_rts = get_external_rts(
                    cfn_client, spoke["account-name"], external_rts_ids
                )
                for external_rt in external_rts:
                    routes = get_routes(ec2_client, external_rt)
                    for route in routes:
                        if route not in vpc_default_routes:
                            if route.get(
                                "DestinationCidrBlock"
                            ) == "0.0.0.0/0" and route.get("NatGatewayId").startswith(
                                "nat-"
                            ):
                                pass
                            else:
                                print(
                                    f"Route {route} is not matching the expected architecture in {external_rt} external route table"
                                )
    except Exception as e:
        logger.error("Error checking route tables for the account:")
        logger.error(e)
        raise Exception("Error checking route tables for the account.")


def get_external_rts(cfn_client, spoke_name, external_rts_ids):
    try:
        external_rts = []
        for external_rt in external_rts_ids:
            response = cfn_client.describe_stack_resources(
                StackName=f"{spoke_name}-NETWORK-STACK",
                LogicalResourceId=external_rt,
            )["StackResources"][0]["PhysicalResourceId"]
            external_rts.append(response)
        return external_rts
    except Exception as e:
        logger.error("Error describing external subnet route tables:")
        logger.error(e)
        raise Exception("Error describing external subnet route tables")


def check_drift_detection(cfn_client, spoke_name):
    try:
        stack_drift_detection_id = detect_stack_drift(cfn_client, spoke_name)
        while True:
            drift_detection = describe_drift_detection(
                cfn_client, stack_drift_detection_id
            )
            if drift_detection["DetectionStatus"] in (
                "DETECTION_COMPLETE",
                "DETECTION_FAILED",
            ):
                return drift_detection
            time.sleep(5)
    except Exception as e:
        logger.error("Error checking network stack drift:")
        logger.error(e)
        raise Exception("Error checking network stack drift.")


def describe_drift_detection(cfn_client, stack_drift_detection_id):
    try:
        response = cfn_client.describe_stack_drift_detection_status(
            StackDriftDetectionId=stack_drift_detection_id
        )
        return response
    except Exception as e:
        logger.error("Error describing network stack drift detection status:")
        logger.error(e)
        raise Exception("Error describing network stack drift detection status.")


def detect_stack_drift(cfn_client, spoke_name):
    try:
        response = cfn_client.detect_stack_drift(
            StackName=f"{spoke_name}-NETWORK-STACK",
        )["StackDriftDetectionId"]
        return response
    except Exception as e:
        logger.error("Error checking network stack drift:")
        logger.error(e)
        raise Exception("Error checking network stack drift.")


def check_cnx_routes(spoke_info, route_tables):
    try:
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
        ]

        additional_routes_dict = {
            "eu-west-1": ["159.43.97.0/24", "159.43.118.0/24"],
            "us-east-1": [],
            "us-east-2": [],
            "ap-southeast-1": [],
            "ap-southeast-2": [],
            "ap-southeast-3": [],
        }

        exempt_routes = ["100.64.0.0/16", "0.0.0.0/0", spoke_info["ip-range"]]
        dest_cidr_blocks = (
            default_routes
            + additional_routes_dict.get(spoke_info["region"])
            + exempt_routes
        )

        for route_table in route_tables:
            for route in route_table["Routes"]:
                if route.get("DestinationCidrBlock") not in dest_cidr_blocks:
                    logger.info(
                        f"Incompliant route {route['DestinationCidrBlock']} in {route_table['RouteTableId']} route table."
                    )

    except Exception as e:
        logger.error(e)


def get_routes(ec2_client, rt_id):
    try:
        routes = ec2_client.describe_route_tables(
            RouteTableIds=[
                rt_id,
            ],
        )[
            "RouteTables"
        ][0]["Routes"]
        return routes
    except Exception as e:
        logger.error("Error getting routes:")
        logger.error(e)
        raise Exception("Error getting routes.")


def get_route_tables(ec2_client, rt_type):
    try:
        route_tables = ec2_client.describe_route_tables(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        rt_type,
                    ],
                }
            ]
        )["RouteTables"]
        return route_tables
    except Exception as e:
        logger.error("Error getting route tables:")
        logger.error(e)
        raise Exception("Error getting route tables.")


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
