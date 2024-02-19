"""
[H&S] - Gets list of all "Connected" spokes from Dynamo DB that has status:"active" and also use
the environment-type field to target Prod and NonProd environments for the segmented migration.
Connects to each Connected spoke via role session.
This script should disassociate any spokes currently associated with the NonProd or Prod TGW
route tables and associate the TGW attachment ID with the OnPrem TGW route table.
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

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Global variables
hub_account_id = os.environ["HUB_ID"]
hub_account_name = os.environ["HUB_NAME"]
environment_type = os.environ["ENVIRONMENT_TYPE"]
region_for_applying_changes = os.environ["REGION_FOR_APPLYING_CHANGES"]
tgw_prod_rt_id = os.environ["TGW_PROD_RT_ID"]
tgw_non_prod_rt_id = os.environ["TGW_NON_PROD_RT_ID"]
tgw_on_prem_rt_id = os.environ["TGW_ON_PREM_RT_ID"]
tgw_id = os.environ["TGW_ID"]

hub_target_role = f"arn:aws:iam::{hub_account_id}:role/CIP_MANAGER"


def lambda_handler(event, _context):
    logger.info(event)
    logger.info(
        "Lambda to disassociate any Active, Connected or IaaS spokes currently associated with the NonProd or Prod "
        "TGW route tables and associate the TGW attachment ID with the OnPrem TGW route table"
    )

    if not event.get("accounts"):
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
    else:
        spoke_accounts = event.get("accounts")

    logger.info(f"Accounts to action: {len(spoke_accounts)}")

    remaining_accounts = {"accounts": spoke_accounts.copy()}
    # Iterate through all the spokes in the list
    for account in spoke_accounts:
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
                logger.info(f"remaining account: {remaining_accounts}")
                logger.error(f"Error invoking lambda: {e}")
                raise e
        try:
            # logger.info("Iterating over account item: " + str(account['account-name']))
            # Define variables
            spoke_account_id = account["account"]
            spoke_account_name = str(account["account-name"])
            spoke_target_role = f"arn:aws:iam::{spoke_account_id}:role/CIP_MANAGER"
            spoke_region = str(account["region"])
            # Assume role in spoke account and get EC2 resource session
            logger.info(
                f"Creating Session in {spoke_region} for account: {spoke_account_name}"
            )
            spoke_session = _get_role_session(
                region_name=spoke_region,
                target_role_arn=spoke_target_role,
                session_policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ec2:DescribeTransitGateway*",
                                "ec2:DescribeVpcs",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            )
            logger.info(spoke_session)

            spoke_tgw_response = _get_spoke_tgw_details(
                spoke_session, spoke_account_name, spoke_account_id, spoke_region
            )
            # Migrate spoke to On-Prem TGW Route table
            logger.info(
                f"Creating Hub Session in {spoke_region} for account: {hub_account_name}"
            )
            hub_session = _get_role_session(
                region_name=spoke_region,
                target_role_arn=hub_target_role,
                session_policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ec2:AssociateTransitGatewayRouteTable",
                                "ec2:DisassociateTransitGatewayRouteTable",
                                "ec2:CreateTransitGatewayRoute",
                                "ec2:DescribeTransitGateway*",
                                "ec2:EnableTransitGatewayRouteTablePropagation",
                                "ec2:CreateTransitGatewayRoute",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            )
            logger.info(hub_session)
            _migrate_spoke(
                hub_session,
                spoke_tgw_response,
                spoke_session,
                spoke_account_id,
                spoke_account_name,
                spoke_region,
            )
            time.sleep(0.2)
            remaining_accounts["accounts"].remove(account)
        except Exception as e:
            logger.info(f"remaining account: {remaining_accounts}")
            logger.critical(
                f"Error in migrating spoke to On-Prem TGW Route table in region {region_for_applying_changes}: {e}",
                exc_info=1,
            )


def _get_spoke_cidr(spoke_session, tgw_attachment_id):
    ec2_spoke_client = spoke_session.client("ec2")
    response = ec2_spoke_client.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[tgw_attachment_id]
    )
    vpc_id = response["TransitGatewayVpcAttachments"][0]["VpcId"]
    vpc_details = ec2_spoke_client.describe_vpcs(VpcIds=[vpc_id])
    vpc_cidr = vpc_details["Vpcs"][0]["CidrBlock"]
    logger.info(
        f"for tgw attachment {tgw_attachment_id}, with spoke vpc {vpc_id} has spoke CIDR {vpc_cidr}"
    )
    return vpc_cidr


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
        # logger.info(f'Requesting temporary credentials using role: {target_role_arn}')
        credentials = boto3.client("sts").assume_role(
            RoleArn=target_role_arn,
            Policy=json.dumps(session_policy) if session_policy else None,
            RoleSessionName="AssumeRole-MigrateToOnPremRT"[0:64],
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
                "Code": "ERROR Lambda MigrateToOnPremRT",
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

    filter_expression = (
        Attr("status").eq("Active")
        & (Attr("account-type").eq("Connected") | Attr("account-type").eq("IaaS"))
        & Attr("environment-type").eq(environment_type)
        & Attr("region").eq(region_for_applying_changes)
    )

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

    logger.info(f"DDB Scan result: {result}")
    return result


def _get_spoke_tgw_details(
    spoke_session: str,
    spoke_account_name: str,
    spoke_account_id: str,
    spoke_region: str,
):
    """
    Checks if spoke environment-type is Prod or Non Prod,
    Disassociate TGW attachement ID from Prod or Non Prod Route Table and Associate it to On-Prem Route table
    :param spoke_session: EC2 session for spoke account
    :param spoke_account_name: Spoke name
    :param spoke_account_id: ID of AWS spoke account
    :param region: Region name
    """

    ec2_client = spoke_session.client("ec2")
    # Describe VPCs
    response = ec2_client.describe_transit_gateway_attachments(
        Filters=[
            {"Name": "transit-gateway-id", "Values": [tgw_id]},
            {"Name": "resource-type", "Values": ["vpc"]},
            {"Name": "resource-owner-id", "Values": [spoke_account_id]},
        ]
    )
    # logger.info(f"Describe transit gateway attachment information for {spoke_account_name} for transit gateway {tgw_id} in region {spoke_region}: {response}")
    return response


def _migrate_spoke(
    hub_session,
    spoke_tgw_response,
    spoke_session,
    spoke_account_id,
    spoke_account_name,
    spoke_region,
):
    """
    Checks if spoke environment-type is Prod or Non Prod
    Disassociate TGW attachement ID from Prod or Non Prod Route Table and Associate it to On-Prem Route table
    :param hub_session: EC2 session for hub account
    :param spoke_tgw_response: tgw response details for spoke account
    :param spoke_session: EC2 session for spoke account
    :param spoke_account_name: Spoke name
    :param region: Region name
    """

    ec2_hub_client = hub_session.client("ec2")
    try:
        # Testing only - to be removed - Associate to non-prod rt
        # tgw_route_table_id = 'tgw-rtb-0aff0ec6a5913e75f'
        # tgw_on_prem_rt_id = 'tgw-rtb-03fbb1c6200a78eea'
        # tgw_attachment_id = 'tgw-attach-072acb9642e5c200b'
        # # _disassociate_from_nonprod_or_prod_tgw_rt(ec2_hub_client, tgw_on_prem_rt_id, tgw_attachment_id,
        # #                                           spoke_account_name, spoke_region)
        # _associate_to_on_premise_tgw_rt(ec2_hub_client, tgw_route_table_id, tgw_attachment_id, spoke_account_name,
        #                                  spoke_region)

        if spoke_tgw_response.get("TransitGatewayAttachments"):
            for each_tgw_attachment in spoke_tgw_response.get(
                "TransitGatewayAttachments", []
            ):
                tgw_attachment_id = each_tgw_attachment.get(
                    "TransitGatewayAttachmentId"
                )
                spoke_cidr = _get_spoke_cidr(spoke_session, tgw_attachment_id)
                logger.info(
                    f"Adding static routes to On Premise Route table {tgw_on_prem_rt_id} with tgw attachment "
                    f"{tgw_attachment_id} for spoke {spoke_account_name} in region {spoke_region}"
                )
                _create_tgw_static_route(
                    ec2_hub_client, tgw_on_prem_rt_id, tgw_attachment_id, spoke_cidr
                )
                if not each_tgw_attachment.get("Association"):
                    # logger.info(f"No existing association found. Initiate association to On-Prem Route table "
                    #             f"for {spoke_account_name} in region{spoke_region}")
                    _associate_to_on_premise_tgw_rt(
                        ec2_hub_client,
                        tgw_on_prem_rt_id,
                        tgw_attachment_id,
                        spoke_account_name,
                        spoke_region,
                    )
                else:
                    tgw_route_table_dict = each_tgw_attachment.get("Association")
                    tgw_route_table_id = tgw_route_table_dict[
                        "TransitGatewayRouteTableId"
                    ]
                    if tgw_route_table_id == tgw_on_prem_rt_id:
                        logger.info(
                            f"Spoke account {spoke_account_name} in region {spoke_region} is already associated to On-Prem TGW Route Table. Skipping this one ... "
                        )
                        continue
                    _disassociate_from_nonprod_or_prod_tgw_rt(
                        ec2_hub_client,
                        tgw_route_table_id,
                        tgw_attachment_id,
                        spoke_account_name,
                        spoke_region,
                    )
                    _check_disassociation_status_and_wait(
                        spoke_session,
                        spoke_account_name,
                        spoke_account_id,
                        spoke_region,
                    )
                    _associate_to_on_premise_tgw_rt(
                        ec2_hub_client,
                        tgw_on_prem_rt_id,
                        tgw_attachment_id,
                        spoke_account_name,
                        spoke_region,
                    )

        else:
            logger.info(
                f"There is no Transit Gateway Attachments in the spoke account: {spoke_account_name} in {spoke_region}"
            )

    except Exception as e:
        logger.critical(
            {
                "Code": "ERROR Lambda MigrateToOnPremRT",
                "Message": "Error migrating spokes to OnPrem TGW Route Table from Prod or Non-Prod",
            }
        )
        raise e


def _disassociate_from_nonprod_or_prod_tgw_rt(
    ec2_hub_client,
    tgw_route_table_id,
    tgw_attachment_id,
    spoke_account_name,
    spoke_region,
):
    logger.info(
        f"Spoke account {spoke_account_name} in region {spoke_region}, disassociating {environment_type} TGW route table"
    )
    logger.info(f"{tgw_route_table_id} and {tgw_attachment_id} and {tgw_on_prem_rt_id}")
    response_disassociate = ec2_hub_client.disassociate_transit_gateway_route_table(
        TransitGatewayRouteTableId=tgw_route_table_id,
        TransitGatewayAttachmentId=tgw_attachment_id,
    )
    logger.info(
        f"Response when disassociating spoke {spoke_account_name} from NonProd or Prod TGW Route Table: {response_disassociate}"
    )
    return


def _associate_to_on_premise_tgw_rt(
    ec2_hub_client,
    tgw_on_prem_rt_id,
    tgw_attachment_id,
    spoke_account_name,
    spoke_region,
):
    logger.info(
        f"Spoke account {spoke_account_name} in region {spoke_region}, initiate association to On-Prem TGW Route Table"
    )
    response_associate = ec2_hub_client.associate_transit_gateway_route_table(
        TransitGatewayRouteTableId=tgw_on_prem_rt_id,
        TransitGatewayAttachmentId=tgw_attachment_id,
    )
    logger.info(
        f"Response when associating spoke {spoke_account_name} to On Premise TGW Route Table: {response_associate}"
    )
    return


def _check_disassociation_status_and_wait(
    spoke_session, spoke_account_name, spoke_account_id, spoke_region
):
    disassociation_status = _get_spoke_tgw_details(
        spoke_session, spoke_account_name, spoke_account_id, spoke_region
    )
    if disassociation_status.get("TransitGatewayAttachments"):
        for each_tgw_attachment in disassociation_status.get(
            "TransitGatewayAttachments", []
        ):
            if not each_tgw_attachment.get("Association"):
                logger.info(
                    f"No existing association found. Initiate association to On-Prem Route table "
                    f"for {spoke_account_name} in region{spoke_region}"
                )
                return
            else:
                # logger.info("waiting for disassociation to complete")
                time.sleep(5)
                _check_disassociation_status_and_wait(
                    spoke_session, spoke_account_name, spoke_account_id, spoke_region
                )
    return


def _create_tgw_static_route(
    ec2_hub_client, tgw_route_table_id, tgw_attachment_id, spoke_cidr
):
    """
    Creates a Transit Gateway Route in the Transit Gateway Route Table whose ID equals the one
    passed to the function. The route is created with the Spoke's CIDR range. The Association ID
    is also required
    """
    dest_cidr_block = str(spoke_cidr)
    try:
        ec2_hub_client.create_transit_gateway_route(
            DestinationCidrBlock=dest_cidr_block,
            TransitGatewayRouteTableId=tgw_route_table_id,
            TransitGatewayAttachmentId=tgw_attachment_id,
        )
        logger.info(f"Successfully added route to route table {tgw_route_table_id}!")
    except Exception as e:
        logger.info(f"Error adding route to ON-PREMISE TGW RT: {e}")
    return
