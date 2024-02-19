#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="service-quota-increase"
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


def main(hub_env, environment_type):
    try:
        connected_accounts = get_connected_spokes(hub_env, environment_type)

        for account in connected_accounts:
            account_number = account["account"]["S"]
            role = f"arn:aws:iam::{account_number}:role/CIP_MANAGER"
            region = account["region"]["S"]
            client = create_client("service-quotas", role, region)
            quotacode = "L-93826ACB"

            get_quotas = client.get_service_quota(
                ServiceCode="vpc", QuotaCode=quotacode
            )

            if get_quotas["Quota"]["Value"] < 100.0:
                LOGGER.info(
                    f"Increasing quota limit for account number: {account_number} in region {region}"
                )
                client.request_service_quota_increase(
                    ServiceCode="vpc", QuotaCode=quotacode, DesiredValue=100.0
                )
            else:
                LOGGER.info(
                    f"Not increasing quota limit for account number {account_number}  as current quota limit is {get_quotas['Quota']['Value']}"
                )
    except Exception as e:
        logging.error(e)


def get_connected_spokes(hub_env, environment_type):
    table_name = f"WH-{hub_env}-DYN_METADATA"
    params = {
        "TableName": table_name,
        "FilterExpression": "#s = :active AND #ct = :connected AND #env = :environment",
        "Select": "SPECIFIC_ATTRIBUTES",
        "ProjectionExpression": "#c, account, #ct",
        "ExpressionAttributeNames": {
            "#c": "region",
            "#s": "status",
            "#ct": "account-type",
            "#env": "environment-type",
        },
        "ExpressionAttributeValues": {
            ":active": {"S": "Active"},
            ":connected": {"S": "Connected"},
            ":environment": {"S": environment_type},
        },
    }

    result = []
    client = boto3.client("dynamodb", "eu-west-1")
    while True:
        response = client.scan(**params)
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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("hub_env", type=str)
    parser.add_argument("environment_type", type=str)
    args = parser.parse_args()
    main(args.hub_env, args.environment_type)
