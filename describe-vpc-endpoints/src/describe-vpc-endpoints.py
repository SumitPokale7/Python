# Standard library imports
import logging
import csv
from typing import List, Optional
from io import StringIO

# Third party / External library imports
import boto3
import simplejson as json
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, ConditionBase

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

hub_account_id = os.environ["HUB_ID"]
hub_account_name = os.environ["HUB_NAME"]
hub_target_role = f"arn:aws:iam::{hub_account_id}:role/CIP_MANAGER"
bucket_name = os.environ["BUCKET_NAME"]
bucket_key = f"{hub_account_name}-VPC-ENDPOINTS.csv"


def lambda_handler(event, context):
    try:
        # Other event parameters
        filtered_services = event.get("filtered_services")
        account_types = event.get("account_types", ["Standalone", "Connected"])

        # Use provided accounts if passed in the event, otherwise query DynamoDB
        accounts = event.get("accounts")
        if not accounts:
            # Initialize an empty list to hold all spokes
            spoke_list = []
            for account_type in account_types:
                account_filter = (
                    Attr("account-type").eq(account_type)
                    & Attr("status").eq("Active")
                )
                spoke_list.extend(_get_spoke_accounts(hub_account_name, account_filter))
            logger.info(f"Total accounts to action: {len(spoke_list)}")
            accounts_filter = ["account", "account-name", "account-type", "account-description", "environment-type", "region"]
            spoke_list = [{key: d[key] for key in accounts_filter if key in d} for d in spoke_list]
        else:
            spoke_list = accounts
        remaining_accounts = spoke_list.copy()

        # Initialize CSV output and append data if this is a reinvocation
        output = StringIO()
        if "output_data" in event:
            output.write(event["output_data"])
        else:
            csv_writer = csv.writer(output)
            csv_writer.writerow(["AccountName", "AccountId", "AccountType", "EnvironmentType", "AccountDescription", "Region",  "VpcEndpointId", "VpcEndpointType", "ServiceName", "EndpointName"])

        csv_writer = csv.writer(output)

        for spoke in spoke_list:
            spoke_target_role = f"arn:aws:iam::{spoke['account']}:role/CIP_MANAGER"
            spoke_session = _get_role_session(
                target_role_arn=spoke_target_role,
                session_policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ec2:DescribeVpcEndpoints",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            )

            vpc_endpoints = _get_vpc_endpoints(spoke_session, spoke['region'], filtered_services)
            for vpc_endpoint in vpc_endpoints:
                endpoint_name = None
                if "Tags" in vpc_endpoint:
                    for tag in vpc_endpoint["Tags"]:
                        if tag["Key"] == "Name":
                            endpoint_name = tag["Value"]
                            break
                csv_writer.writerow([
                    spoke["account-name"],
                    spoke["account"],
                    spoke["account-type"],
                    spoke["environment-type"],
                    spoke["account-description"],
                    spoke["region"],
                    vpc_endpoint["VpcEndpointId"],
                    vpc_endpoint["VpcEndpointType"],
                    vpc_endpoint["ServiceName"],
                    endpoint_name
                ])
            remaining_accounts.remove(spoke)
            logger.info(f"Remaining accounts: {len(remaining_accounts)}")
            if context.get_remaining_time_in_millis() < 30000:  # 30 seconds before timeout
                try:
                    lambda_client = boto3.client("lambda")
                    event.update({
                        "accounts": remaining_accounts,
                        "output_data": output.getvalue(),
                    })
                    lambda_client.invoke(
                        FunctionName=context.invoked_function_arn,
                        InvocationType='Event',
                        Payload=json.dumps(event, use_decimal=True),
                    )
                    return
                except Exception as e:
                    logger.info(f"Remaining accounts: {remaining_accounts['accounts']}")
                    logger.error(f"Error invoking lambda: {e}")
                    raise e

        # Upload CSV to S3
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=bucket_key,
            Body=output.getvalue(),
            ContentType="text/csv"
        )
        logger.info(f"Uploaded VPC endpoints data to s3://{bucket_name}/{bucket_key}")

    except Exception as e:
        logger.critical(
            {
                "Code": "ERROR Lambda Describe VPC Endpoints",
                "Message": f"Unhandled exception occurred when processing the request: {e}",
            }
        )


def _get_spoke_accounts(hub_account_name: str, filter_expression: ConditionBase) -> List[dict]:
    """
    Scan DynamoDB Table to get all spoke accounts in Active status.
    :param hub_account_name: Hub name
    :param filter_expression: Filter expression for DynamoDB scan
    :return: List of spoke accounts
    """
    hub_session = _get_hub_session()
    metadata_table = hub_session.resource("dynamodb", region_name="eu-west-1").Table(hub_account_name + "-DYN_METADATA")
    logger.info("Scanning over DDB table: " + metadata_table.table_name)

    params = {"FilterExpression": filter_expression}
    accounts = []
    count = 0

    while True:
        response = metadata_table.scan(**params)

        for item in response.get("Items", []):
            accounts.append(item)
            count += 1
        if not response.get("LastEvaluatedKey"):
            break

        params.update({"ExclusiveStartKey": response["LastEvaluatedKey"]})
    logger.info(f"Count of accounts to be addressed: {count}")
    return accounts


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
                        "s3:PutObject",
                    ],
                    "Resource": f"arn:aws:dynamodb:eu-west-1:{hub_account_id}:table/{hub_account_name}-DYN_METADATA",
                },
            ],
        },
    )
    return hub_session


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
            RoleSessionName="AssumeRole-Describe-VPC-Endpoints"[0:64],
        )["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda Describe VPC Endpoints",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def _get_vpc_endpoints(spoke_session, region: str, filtered_services: Optional[List[str]] = None):
    """
    Get list of VPC endpoints in the spoke account and filter by specific services if provided.
    :param spoke_session: boto3 session for the spoke account.
    :param region: spoke AWS region to query the VPC endpoints.
    :param filtered_services: List of service names to filter the VPC endpoints. If None, returns all endpoints.
    :return: List of filtered VPC endpoints
    """
    try:
        ec2_client = spoke_session.client("ec2", region_name=region)
        vpc_endpoints = ec2_client.describe_vpc_endpoints()["VpcEndpoints"]
        if filtered_services:
            filtered_services = [f"com.amazonaws.{region}.{service}" for service in filtered_services]
            vpc_endpoints = [
                vpc_endpoint for vpc_endpoint in vpc_endpoints
                if vpc_endpoint["ServiceName"] in filtered_services
            ]

        return vpc_endpoints
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda Describe VPC Endpoints",
                "Message": "Error retrieving the endpoints.",
            }
        )
        raise e
