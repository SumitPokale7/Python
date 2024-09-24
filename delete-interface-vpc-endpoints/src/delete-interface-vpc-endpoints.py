import boto3
import json
import logging
from botocore.exceptions import ClientError

# Set logger
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)


def _get_role_session(target_role_arn: str, session_policy: str = None, **kwargs):
    try:
        credentials = boto3.client("sts").assume_role(
            RoleArn=target_role_arn,
            Policy=json.dumps(session_policy) if session_policy else None,
            RoleSessionName="AssumeRole-EndPoint"[0:64],
        )["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def delete_vpc_interface_endpoints(account_id, region_name, endpoint_ids, spoke_session):
    try:
        # Create boto3 client for EC2
        ec2_client = spoke_session.client("ec2", region_name)

        # Delete the VPC interface endpoints
        for endpoint_id in endpoint_ids:
            ec2_client.delete_vpc_endpoints(VpcEndpointIds=[endpoint_id])
            logger.info(f"VPC interface endpoint {endpoint_id} deleted successfully.")
    except Exception as e:
        logger.critical(f"Failed to delete VPC interface endpoints for account {account_id} in region {region_name}: {str(e)}")
        raise e


def lambda_handler(event, context):
    for account in event.get('accounts', []):
        account_id = account['account_id']
        region = account['region']
        endpoint_ids = account['endpoint_ids']

        spoke_target_role = f"arn:aws:iam::{account_id}:role/CIP_MANAGER"
        spoke_session = _get_role_session(
            target_role_arn=spoke_target_role,
            session_policy={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["ec2:DeleteVpcEndpoints"],
                        "Resource": "*",
                    },
                ],
            },
        )

        try:
            delete_vpc_interface_endpoints(account_id, region, endpoint_ids, spoke_session)
        except Exception as e:
            logger.error(f"Failed to delete endpoint IDs for account {account_id} in region {region}: {str(e)}")
            raise e
