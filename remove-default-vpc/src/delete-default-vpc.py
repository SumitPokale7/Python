"""
[H&S] - Gets list of all spokes from Dynamo DB that has status:"active"
Connects to each spoke via role session and deletes default VPC in Osaka (ap-northeast-3) region only
"""

# Standard library imports
import os
import time
import logging
from typing import List

# Third party / External library imports
import boto3
import json
from boto3.dynamodb.conditions import Attr

# from botocore.exceptions import ClientError

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Global variables
hub_account_id = os.environ["HUB_ID"]
hub_account_name = os.environ["HUB_NAME"]
region = os.environ["OSAKA_REGION"]
hub_target_role = f"arn:aws:iam::{hub_account_id}:role/CIP_MANAGER"


def lambda_handler(event, _context):
    logger.info(event)
    logger.info("Lambda to delete default VPC in active spoke account in Osaka region")
    # Assume role in hub account and get DDB resource session
    logger.info(f"Creating EC2 Session for account: {hub_account_name}")
    hub_session = _get_role_session(
        region_name=os.environ["AWS_REGION"],
        target_role_arn=hub_target_role,
        session_policy={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:Scan",
                    ],
                    "Resource": f"arn:aws:dynamodb:eu-west-1:{hub_account_id}:table/{hub_account_name}-DYN_METADATA",
                },
            ],
        },
    )
    logger.info(hub_session)

    # Get list of active spoke accounts
    spoke_accounts = _get_spoke_accounts(hub_session, hub_account_name)

    # Iterate through all the spokes in the list
    for account in spoke_accounts:
        try:
            if account["account"] == hub_account_id:
                logger.info(
                    f"Hub (Orgs Master) {hub_account_id} account is not a spoke, skipping..."
                )
                continue
            logger.info("Iterating over account item: " + str(account["account-name"]))
            # Define variables
            spoke_account_id = account["account"]
            spoke_account_name = str(account["account-name"])
            spoke_target_role = f"arn:aws:iam::{spoke_account_id}:role/CIP_MANAGER"
            # Assume role in spoke account and get EC2 resource session
            logger.info(
                f"Creating EC2 Session in {region} for account: {spoke_account_name}"
            )
            spoke_session = _get_role_session(
                region_name=region,
                target_role_arn=spoke_target_role,
                session_policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ec2:*",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            )
            logger.info(spoke_session)
            # Delete default VPC in spoke account
            logger.info(
                f"Deleting the default VPC in spoke {spoke_account_name} account in {region}..."
            )
            _spoke_expunge_default_vpc(spoke_session, spoke_account_name, region)
            time.sleep(0.2)
        except Exception as e:
            logger.critical(
                f"Error in {spoke_account_name} ({region}): {e}", exc_info=1
            )


def _get_role_session(
    target_role_arn: str, session_policy: str = None, region_name: str = None, **kwargs
):
    """
    Creates a session policy as an inline policy on the fly
    and passes in the session during role assumption
    :param target_role_arn: Arn of target role
    :param session_policy: IAM inline policy
    :param region_name: AWS region where the role is assumed
    :return: boto3.session
    """

    try:
        logger.info(f"Requesting temporary credentials using role: {target_role_arn}")
        credentials = boto3.client("sts").assume_role(
            RoleArn=target_role_arn,
            Policy=json.dumps(session_policy) if session_policy else None,
            RoleSessionName="AssumeRole-DeleteDefaultVPC"[0:64],
        )["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region_name,
        )
    except Exception as e:
        logger.critical(
            {
                "Code": "ERROR Lambda DefaultVPCDeletion",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def _get_spoke_accounts(hub_session: str, hub_account_name: str) -> List[dict]:
    """
    Scan DynamoDB Table to get all spoke accounts in Active status
    :param hub_session: EC2 session for hub account
    :param hub_account_name: Hub name
    :return: result
    """

    metadata_table = hub_session.resource("dynamodb", region_name="eu-west-1").Table(
        hub_account_name + "-DYN_METADATA"
    )
    logger.info("Scanning over DDB table: " + metadata_table.table_name)

    filter_expression = Attr("status").eq("Active")
    params = {"FilterExpression": filter_expression}

    result = []

    while True:
        response = metadata_table.scan(**params)

        for item in response.get("Items", []):
            result.append(item)

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )

    return result


def _delete_vpc_dependencies(spoke_session: str, vpc_id: str, region: str):
    """
    Deletes default VPC dependencies such as subnets and IGW
    :param spoke_session: EC2 session for spoke account
    :param vpc_id: Id of the default VPC
    :param region: Region name
    """

    # Define vars
    ec2_client = spoke_session.client("ec2")
    # Describe IGW associated with the vpc
    resp_desc_igws = ec2_client.describe_internet_gateways(
        Filters=[
            {"Name": "attachment.vpc-id", "Values": [vpc_id]},
        ],
    )["InternetGateways"]
    logger.info(resp_desc_igws)
    for item in resp_desc_igws:
        # Detach the IGW
        igw_id = item.get("InternetGatewayId")
        logger.info(
            f"Detaching Internet Gateway ID: {igw_id} from {vpc_id} in {region}"
        )
        logger.info(
            ec2_client.detach_internet_gateway(
                InternetGatewayId=igw_id, VpcId=vpc_id, DryRun=False
            )
        )

        # Delete the IGW
        logger.info(f"Deleting Internet Gateway ID: {igw_id} in {region}")
        logger.info(
            ec2_client.delete_internet_gateway(InternetGatewayId=igw_id, DryRun=False)
        )

    # Describe subnets in VPC
    resp_desc_subnets = ec2_client.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
        ],
    )["Subnets"]
    logger.info(resp_desc_subnets)

    # Delete all subnets
    if len(resp_desc_subnets) > 0:
        for item in resp_desc_subnets:
            subnet_id = item.get("SubnetId")
            logger.info(f"Deleting Subnet ID: {subnet_id} in {region}")
            logger.info(ec2_client.delete_subnet(SubnetId=subnet_id, DryRun=False))


def _spoke_expunge_default_vpc(
    spoke_session: str, spoke_account_name: str, region: str
):
    """
    Checks if default VPC is present in spoke account, and deletes its dependencies
    Deletes default VPC itself
    :param spoke_session: EC2 session for spoke account
    :param spoke_account_name: Spoke name
    :param region: Region name
    """

    ec2_client = spoke_session.client("ec2")
    # Describe VPCs
    response = ec2_client.describe_vpcs()
    try:
        if response.get("Vpcs"):
            for vpc in response.get("Vpcs", []):
                vpc_id = vpc.get("VpcId")
                is_default_vpc = True if vpc.get("IsDefault") is True else False
                if is_default_vpc:
                    logger.info(f"Found the default VPC: {vpc_id}")

                    # Delete dependencies (calling method)
                    logger.info(
                        f"Deleting VPC: {vpc_id} dependencies for spoke account ID: {spoke_account_name} in {region}"
                    )
                    _delete_vpc_dependencies(
                        spoke_session,
                        vpc_id,
                        region,
                    )

                    # Delete VPC
                    logger.info(
                        f"Deleting VPC: {vpc_id} in spoke account ID: {spoke_account_name} in {region}"
                    )
                    logger.info(
                        ec2_client.delete_vpc(
                            VpcId=vpc_id,
                        )
                    )
                else:
                    logger.info(f"The {vpc_id} is not a default VPC, skipping...")

        else:
            logger.info(
                f"There is no VPC(s) in the spoke account: {spoke_account_name} in {region}"
            )

    except Exception as e:
        logger.critical(
            {
                "Code": "ERROR Lambda DefaultVPCDeletion",
                "Message": "Error deleting default VPC",
            }
        )
        raise e


# # Run test locally - update hub account details
# if __name__ == "__main__":

#     logger = logging.getLogger(__name__)
#     FORMAT = "[%(name)8s()]: %(message)s"
#     logging.basicConfig(format=FORMAT, level=logging.INFO)
#     # Define vars, replace with you hub account details
#     # Event details
#     event = {
#       "Action": "DeleteDefaultVPC"
#     }
#     _context = []
#     lambda_handler(event, _context)
