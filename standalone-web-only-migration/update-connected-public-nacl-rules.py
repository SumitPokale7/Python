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


def main(hub_env, environment_type):
    try:
        table_name = f"{hub_env}-DYN_METADATA"

        accounts_filter = (
            Attr("internet-facing").eq(True)
            & Attr("network-web-only").eq(True)
            & Attr("network-type").eq("Connected-4-Tier-3-AZ")
            & Attr("environment-type").eq(environment_type)
            & Attr("status").eq("Active")
        )

        spoke_list = get_spokes(table_name, accounts_filter)

        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/AWS_PLATFORM_ADMIN"
            region = spoke["region"]
            ec2_client = create_client("ec2", role, region)
            logger.info(f"Updating public NACLs of {spoke['account-name']} account.")
            public_nacl = get_nacl_id(ec2_client)
            duplicate_nacl_rules(ec2_client, public_nacl)
            # Creating rule 400
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
            # Creating/Updating rule 200
            replace_nacl_rule(
                ec2_client,
                "10.0.0.0/8",
                False,
                public_nacl,
                1024,
                65535,
                "6",
                "allow",
                200,
            )
    except Exception as e:
        logger.error(e)


def duplicate_nacl_rules(ec2_client, public_nacl):
    nacl_entries = ec2_client.describe_network_acls(
        NetworkAclIds=[public_nacl],
    )[
        "NetworkAcls"
    ][0]["Entries"]

    allowed_200_rules = [
        {
            "CidrBlock": "0.0.0.0/0",
            "Egress": False,
            "PortRange": {"From": 1024, "To": 65535},
            "Protocol": "6",
            "RuleAction": "allow",
            "RuleNumber": 200,
        },
        {
            "CidrBlock": "10.0.0.0/8",
            "Egress": False,
            "PortRange": {"From": 1024, "To": 65535},
            "Protocol": "6",
            "RuleAction": "allow",
            "RuleNumber": 200,
        },
    ]

    for nacl_rule in nacl_entries:
        if nacl_rule["RuleNumber"] == 400 and nacl_rule["Egress"] is False:
            if nacl_rule == {
                "CidrBlock": "100.64.0.0/16",
                "Egress": False,
                "PortRange": {"From": 1024, "To": 65535},
                "Protocol": "6",
                "RuleAction": "allow",
                "RuleNumber": 400,
            }:
                logger.info("Rule 400 already matches the architecture.")
            else:
                logger.info(
                    "Rule number 400 has unexpected values duplicating it to rule number 401."
                )
                logger.info(nacl_rule)
                port_range = nacl_rule.get("PortRange", {"From": 0, "To": 65535})
                create_nacl_rule(
                    ec2_client,
                    nacl_rule["CidrBlock"],
                    nacl_rule["Egress"],
                    public_nacl,
                    port_range["From"],
                    port_range["To"],
                    nacl_rule["Protocol"],
                    nacl_rule["RuleAction"],
                    401,
                )
                logger.info("Removing the rule number 400.")
                remove_nacl_rule(ec2_client, nacl_rule["Egress"], public_nacl)
        elif nacl_rule["RuleNumber"] == 200 and nacl_rule["Egress"] is False:
            if nacl_rule not in allowed_200_rules:
                logger.info(
                    "Rule number 200 has unexpected values duplicating it to rule number 201."
                )
                logger.info(nacl_rule)
                port_range = nacl_rule.get("PortRange", {"From": 0, "To": 65535})
                create_nacl_rule(
                    ec2_client,
                    nacl_rule["CidrBlock"],
                    nacl_rule["Egress"],
                    public_nacl,
                    port_range["From"],
                    port_range["To"],
                    nacl_rule["Protocol"],
                    nacl_rule["RuleAction"],
                    201,
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


def replace_nacl_rule(
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
    Replace NACL Rule
    """
    try:
        ec2_client.replace_network_acl_entry(
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
        if e.response["Error"]["Code"] == "InvalidNetworkAclEntry.NotFound":
            logger.info("Route 200 doesn't exist. Creating the 200 rule!")
            create_nacl_rule(
                ec2_client, "10.0.0.0/8", False, nacl_id, 1024, 65535, "6", "allow", 200
            )
        else:
            logger.error("Error replacing network ACL rule:")
            logger.error(e)
            raise Exception("Error replacing network ACL rule.")


def remove_nacl_rule(ec2_client, egress, nacl_id):
    """
    Remove NACL Rule
    """
    try:
        ec2_client.delete_network_acl_entry(
            Egress=egress,
            NetworkAclId=nacl_id,
            RuleNumber=400,
        )
    except Exception as e:
        logger.error("Error removing network ACL rule:")
        logger.error(e)
        raise Exception("Error removing network ACL rule.")


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
    parser.add_argument("environment_type", type=str)
    args = parser.parse_args()
    main(args.hub_env, args.environment_type)
