#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="post-standalone-web-only-migration-cleanup"
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


def main(hub_env, hub_account_id):
    try:
        # Update the spoke list with the accounts you want to migrate
        spoke_list = []
        for spoke in spoke_list:
            spoke_info = get_spoke_details(spoke, hub_env)
            account_number = spoke_info["account"]["S"]
            role = f"arn:aws:iam::{account_number}:role/AWS_PLATFORM_ADMIN"
            region = spoke_info["region"]["S"]
            ec2_client = create_client("ec2", role, region)
            vpc_id = get_vpc_id(ec2_client, spoke_info["ip-range"]["S"])
            logger.info(f"Untagging VPC of {spoke} account.")
            remove_vpc_tag(ec2_client, vpc_id)
            logger.info(f"Updating public NACL of {spoke} account.")
            deploy_public_nacl_rules(
                ec2_client, spoke_info["ip-range"]["S"], spoke_info["account-type"]["S"]
            )
    except Exception as e:
        logger.error(e)


def remove_vpc_tag(ec2_client, vpc_id):
    try:
        ec2_client.delete_tags(
            Resources=[vpc_id], Tags=[{"Key": "network-firewall-enabled"}]
        )
    except Exception:
        raise Exception("Removing VPC tag has failed.")


def get_vpc_id(ec2_client, ip_range):
    try:
        vpc_id = ec2_client.describe_vpcs(
            Filters=[{"Name": "cidr", "Values": [ip_range]}]
        )["Vpcs"][0]["VpcId"]
    except Exception:
        raise Exception("Failed to get VPC id.")
    return vpc_id


def deploy_public_nacl_rules(ec2_client, cidr, account_type):
    public_nacl = get_nacl_id(ec2_client)
    create_nacl_rule(ec2_client, cidr, False, public_nacl, 0, 65535, "-1", "allow", 100)
    create_nacl_rule(
        ec2_client, "0.0.0.0/0", False, public_nacl, 443, 443, "6", "allow", 300
    )
    if account_type == "Standalone":
        create_nacl_rule(
            ec2_client, "0.0.0.0/0", False, public_nacl, 1024, 65535, "6", "allow", 200
        )
    if account_type == "Connected":
        create_nacl_rule(
            ec2_client, "10.0.0.0/8", False, public_nacl, 1024, 65535, "6", "allow", 200
        )
        create_nacl_rule(
            ec2_client,
            "100.64.0.0/16",
            False,
            public_nacl,
            1024,
            65535,
            "6",
            "allow",
            400,
        )
    create_nacl_rule(ec2_client, cidr, True, public_nacl, 0, 65535, "-1", "allow", 100)
    create_nacl_rule(
        ec2_client, "0.0.0.0/0", True, public_nacl, 80, 80, "6", "allow", 200
    )
    create_nacl_rule(
        ec2_client, "0.0.0.0/0", True, public_nacl, 443, 443, "6", "allow", 300
    )
    create_nacl_rule(
        ec2_client, "0.0.0.0/0", True, public_nacl, 1024, 65535, "6", "allow", 400
    )


def get_nacl_id(ec2_client):
    response = ec2_client.describe_network_acls(
        Filters=[
            {
                "Name": "tag:Name",
                "Values": [
                    "public-subnet-nacl",
                ],
            },
        ]
    )["NetworkAcls"][0]["NetworkAclId"]
    return response


def create_nacl_rule(
    ec2_client,
    cidr_block,
    egrees,
    nacl_id,
    range_from,
    range_to,
    protocol,
    action,
    rule_number,
):
    """
    Create NACL Rule
    """
    try:
        ec2_client.create_network_acl_entry(
            CidrBlock=cidr_block,
            Egress=egrees,
            NetworkAclId=nacl_id,
            PortRange={
                "From": range_from,
                "To": range_to,
            },
            Protocol=protocol,
            RuleAction=action,
            RuleNumber=rule_number,
        )
    except Exception as e:
        logger.error("Error creating network ACL rule:")
        logger.error(e)
        raise Exception("Error creating network ACL rule.")


def get_spoke_details(spoke_name, hub_env):
    table_name = f"{hub_env}-DYN_METADATA"
    client = boto3.client("dynamodb", "eu-west-1")
    logger.info(f"Getting all Metadata information for spoke {spoke_name}.")
    response = client.get_item(
        TableName=table_name,
        Key={"account-name": {"S": spoke_name}},
    )
    return response["Item"]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    parser.add_argument("hub_account_id", type=str)
    args = parser.parse_args()
    main(args.hub_env, args.hub_account_id)
