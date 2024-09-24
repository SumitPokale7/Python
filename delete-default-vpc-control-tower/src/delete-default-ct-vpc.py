"""
[H&S] - Connects to each spoke passed in the payload, via role session and deletes default VPC in all regions
"""
# Standard library imports
import time
import logging
from typing import List

# Third party / External library imports
import boto3
import json
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

hub_account_id = os.environ["HUB_ID"]
hub_account_name = os.environ["HUB_NAME"]
hub_target_role = f"arn:aws:iam::{hub_account_id}:role/CIP_MANAGER"


def lambda_handler(event, _context):
    logger.info(event)
    regions = event.get("regions")
    logger.info("Lambda to delete default VPC in spoke account")

    # Get list of active spoke accounts
    accounts = event.get("accounts", _get_spoke_accounts(hub_account_name))
    accounts_ids = [
        item["account"] if isinstance(item, dict) else item for item in accounts
    ]

    logger.info(f"Accounts to action: {len(accounts_ids)}")

    remaining_accounts = {"accounts": accounts_ids.copy(), "regions": regions}
    logger.info(remaining_accounts)
    # Iterate through all the spokes in the list
    for account in accounts_ids:
        if account == hub_account_id:
            logger.info(
                f"Hub (Orgs Master) {hub_account_id} account is not a spoke, skipping..."
            )
            continue
        if _context.get_remaining_time_in_millis() < 60000:  # 60 seconds before timeout
            lambda_client = boto3.client("lambda")
            try:
                response = lambda_client.invoke(
                    FunctionName=_context.function_name,
                    InvocationType="Event",
                    Payload=json.dumps(remaining_accounts),
                )
                logger.info(f"Lambda invoke response: {response}")
                return
            except Exception as e:
                logger.info(f"remaining account: {remaining_accounts['accounts']}")
                logger.error(f"Error invoking lambda: {e}")
                raise e
        try:
            spoke_target_role = f"arn:aws:iam::{account}:role/CIP_MANAGER"
            spoke_session = _get_role_session(
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
            logger.info(f"Deleting the default VPC in spoke {account}...")
            for region in regions:
                logger.info(f"current aws region: {region}")
                _spoke_expunge_default_vpc(spoke_session, account, region)
            time.sleep(0.2)
            remaining_accounts["accounts"].remove(account)
            logger.info(f"remaing accounts: {len(remaining_accounts['accounts'])}")
            print(remaining_accounts)
        except Exception as e:
            logger.info(f"remaining account: {len(remaining_accounts['accounts'])}")
            logger.info(remaining_accounts)
            logger.critical(f"Error While trying to delete default VPC {e}")


def _get_role_session(target_role_arn: str, session_policy: str = None, **kwargs):
    """
    Creates a session policy as an inline policy on the fly
    and passes in the session during role assumption
    :param target_role_arn: Arn of target role
    :param session_policy: IAM inline policy
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
        )
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda DefaultVPCDeletion",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def _get_spoke_accounts(hub_account_name: str) -> List[dict]:
    """
    Scan DynamoDB Table to get all spoke accounts in Active status
    :param hub_session: EC2 session for hub account
    :param hub_account_name: Hub name
    :return: result
    """
    hub_session = _get_hub_session()

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
    ec2_client = spoke_session.client("ec2", region_name=region)
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


def _spoke_expunge_default_vpc(spoke_session: str, account: str, region: str):
    """
    Checks if default VPC is present in spoke account, and deletes its dependencies
    Deletes default VPC itself
    :param spoke_session: EC2 session for spoke account
    :param account: Spoke name
    :param region: Region name
    """

    ec2_client = spoke_session.client("ec2", region_name=region)
    # Describe VPCs
    response = ec2_client.describe_vpcs(
        Filters=[
            {
                "Name": "isDefault",
                "Values": [
                    "true",
                ],
            }
        ]
    )
    try:
        if response.get("Vpcs"):
            for vpc in response.get("Vpcs", []):
                vpc_id = vpc.get("VpcId")
                is_default_vpc = True if vpc.get("IsDefault") is True else False
                if is_default_vpc:
                    logger.info(f"Found the default VPC: {vpc_id}")

                    # Delete dependencies (calling method)
                    logger.info(
                        f"Deleting VPC: {vpc_id} dependencies for spoke account ID: {account} in {region}"
                    )
                    _delete_vpc_dependencies(
                        spoke_session,
                        vpc_id,
                        region,
                    )

                    # Delete VPC
                    logger.info(
                        f"Deleting VPC: {vpc_id} in spoke account ID: {account} in {region}"
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
                f"There is no VPC(s) in the spoke account: {account} in {region}"
            )

    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda DefaultVPCDeletion",
                "Message": "Error deleting default VPC",
            }
        )
        raise e


def _get_hub_session():
    logger.info(f"Creating EC2 Session for account: {hub_account_name}")
    hub_session = _get_role_session(
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
    return hub_session
