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


def main(hub_env):
    try:
        table_name = f"{hub_env}-DYN_METADATA"
        accounts_filter = (
            Attr("status").eq("Active")
            & Attr("account-type").ne("Hub")
        )
        spoke_list = get_spokes(table_name, accounts_filter)
        for spoke in spoke_list:
            account_number = spoke["account"]
            role = f"arn:aws:iam::{account_number}:role/AWSControlTowerExecution"
            iam_client = create_client("iam", role, 'eu-west-1')
            cw_client = create_client("logs", role, 'eu-west-1')
            log_group_name = get_log_group(cw_client)
            if log_group_name:
                logger.info(f"Deleteing log group for {account_number} account.")
                delete_log_group(cw_client, log_group_name)
            logger.info(f"Deleteing LZ admin role for {account_number} account.")
            remove_admin_role(iam_client, 'AWSCloudFormationStackSetExecutionRole')
    except Exception as e:
        logger.error(e)


def get_log_group(cw_client):
    try:
        log_group = cw_client.describe_log_groups(
            logGroupNamePrefix='/aws/lambda/StackSet-AWS-Landing-Zone-IamPasswordPolicyCustomR-'
            )['logGroups']
        if log_group:
            log_group_name = (log_group[0]['logGroupName'])
        else:
            logger.info("Log group doesn't exist in the account.")
            return
    except Exception as e:
        logger.error(e)
        raise Exception("Error while getting the log group information.")
    return log_group_name


def delete_log_group(cw_client, log_group_name):
    try:
        cw_client.delete_log_group(
            logGroupName=log_group_name
        )
    except Exception:
        raise Exception("Failed to delete the log group.")


def remove_admin_role(iam_client, role_name):

    try:
        iam_client.get_role(
            RoleName=role_name
        )
    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            logger.info(f"The {role_name} does not exist in the account.")
            return
        else:
            logger.error(e)
            raise Exception(f"Failed to get the {role_name} role.")

    try:
        role_inline_policies = iam_client.list_role_policies(RoleName=role_name)['PolicyNames']
        for policy in role_inline_policies:
            iam_client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy
            )

        list_attatched_policies = iam_client.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
        for attached_policy in list_attatched_policies:
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn=attached_policy['PolicyArn']
            )

        iam_client.delete_role(RoleName=role_name)
    except Exception as e:
        logger.error(e)
        raise Exception("Failed to delete the role.")


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
