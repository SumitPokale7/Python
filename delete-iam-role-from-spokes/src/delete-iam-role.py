"""
[H&S] - Connects to each spoke passed in the payload, via role session and deletes the iam role
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
    # Get list of active spoke accounts
    accounts = event.get("accounts", _get_spoke_accounts(hub_account_name))
    logger.info("below are the accounts")
    accounts_ids = [
        {"account": item["account"], "account_name": item["account-name"]} for item in accounts if isinstance(item, dict)
    ]
    logger.info("below are account_ids")
    logger.info(accounts_ids)

    logger.info(f"Accounts to action: {len(accounts_ids)}")

    remaining_accounts = {"accounts": accounts_ids.copy()}
    # Iterate through all the spokes in the list
    for acc in accounts_ids:
        if acc["account"] == hub_account_id:
            logger.info(f"Hub (Orgs Master) {hub_account_id} account is not a spoke, skipping...")
            continue
        if _context.get_remaining_time_in_millis() < 60000:  # 60 seconds before timeout
            lambda_client = boto3.client("lambda")
            try:
                response = lambda_client.invoke(
                    FunctionName=_context.function_name,
                    InvocationType="Event",
                    Payload=(remaining_accounts),
                )
                logger.info(f"Lambda invoke response: {response}")
                return
            except Exception as e:
                logger.info(f"remaining account: {remaining_accounts['accounts']}")
                logger.error(f"Error invoking lambda: {e}")
                raise e
        try:
            spoke_account_id = acc["account"]
            policy_arn = 'arn:aws:iam::aws:policy/service-role/AWS_ConfigRole'
            inline_policy = "Allow_S3WriteConfig"
            spoke_target_role = f"arn:aws:iam::{spoke_account_id}:role/CIP_MANAGER"
            spoke_session = _get_role_session(
                target_role_arn=spoke_target_role,
                session_policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "iam:*",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            )
            iam_client = spoke_session.client("iam", region_name="eu-west-1")
            logger.info(spoke_session)
            # Delete iam role from spoke account
            account_name = acc["account_name"]
            role_name = f"{account_name}-platform-config-role"
            logger.info(f"Processing account:{acc} account-name{account_name}...")
            if _config_role_exists(iam_client, role_name):
                logger.info(f"iam role {role_name} exists in the spoke account {acc} ")
                _spoke_detach_iam_policies(iam_client, role_name, policy_arn)
                _spoke_delete_iam_policies(iam_client, role_name, inline_policy)
                _spoke_delete_iam_role(iam_client, role_name)
            else:
                logger.info("config role is not present in the account, Hence No action needed")
            time.sleep(0.2)
            remaining_accounts["accounts"].remove(acc)
            logger.info(f"remaing accounts: {len(remaining_accounts['accounts'])}")
        except Exception as e:
            logger.info(f"remaining account: {len(remaining_accounts['accounts'])}")
            logger.info(remaining_accounts)
            logger.critical(f"Error While trying to delete iam role {e}")


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
            RoleSessionName="AssumeRole-DeleteIAMrole"[0:64],
        )["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.info(f"client error:{e}")
        logger.critical(
            {
                "Code": "ERROR Lambda Roledeletion",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def _get_spoke_accounts(hub_account_name: str) -> List[dict]:
    """
    Scan DynamoDB Table to get all spoke accounts in Active status
    :param hub_session: session for hub account
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


def _get_hub_session():
    logger.info(f"Creating Session for account: {hub_account_name}")
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


def _config_role_exists(iam_client, role_name):

    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except iam_client.exceptions.NoSuchEntityException:
        return False


def _spoke_detach_iam_policies(iam_client, role_name: str, policy_arn: str):

    try:
        response = iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        logger.info(f"Managed policy got detached successfully, response:{response}")
    except ClientError as client_error:
        logger.error(f"Error detaching policy{client_error}")
        raise Exception("Error detaching policy.")


def _spoke_delete_iam_policies(iam_client, role_name: str, policy_name: str):

    try:
        response = iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        logger.info(f"Inline policy {policy_name} got deleted successfully, response:{response}")
    except ClientError as client_error:
        logger.error(f"Error deleting policy:{client_error}")
        raise Exception("Error deleting policy.")


def _spoke_delete_iam_role(iam_client, role_name: str,):

    try:
        response = iam_client.delete_role(RoleName=role_name)
        logger.info(f"role: {role_name} as been deleted successfully, response:{response}")
    except ClientError as client_error:
        logger.error(f"Error deleting Role{client_error}")
        raise Exception("Error deleting Role.")
