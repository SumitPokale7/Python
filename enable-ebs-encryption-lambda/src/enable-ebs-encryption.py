import json
import boto3
import logging
import concurrent.futures
import csv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

regions = [
    "eu-west-2",
    "us-east-2",
    "ap-southeast-2",
    "eu-central-1",
    "ap-southeast-1",
    "eu-west-1",
    "ap-southeast-3",
    "ca-west-1",
    "us-east-1",
]


def read_csv_from_s3(bucket, key):
    try:
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        lines = response["Body"].read().decode("utf-8").splitlines()
        temp = list(csv.DictReader(lines))
        return temp
    except Exception as e:
        logger.error(f"Error accessing s3: {str(e)}")
        raise


def get_boto3_client_federated(account_id, region, role):
    role_temp_credentials = get_temporary_credentials(account_id, role)
    try:
        logger.debug("Creating boto3 client")
        ec2_client = boto3.client(
            "ec2",
            aws_access_key_id=role_temp_credentials["AccessKeyId"],
            aws_secret_access_key=role_temp_credentials["SecretAccessKey"],
            aws_session_token=role_temp_credentials["SessionToken"],
            region_name=region,
        )
        logger.debug("boto3 client created successfully")
        return ec2_client
    except Exception as e:
        logger.error(f"Error creating boto3 client: {str(e)}")
        raise


def get_temporary_credentials(account_id, role):
    try:

        sts_client = boto3.client("sts")
        role_arn = f"arn:aws:iam::{account_id}:role/{role}"
        assumed_role_object = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="LambdaAssumeRoleSession"
        )
        logger.debug(f'Returning temporary credentials for "{role_arn}"')
        return assumed_role_object["Credentials"]
    except Exception as e:
        print(e)


def get_boto3_client(region):
    return boto3.client("ec2", region_name=region)


def ebs_default_encryption(account, no_dry_run):
    """
    Enables EBS encryption by default for all instances
    """
    account_id = account["account-id"]
    account_name = account["account-name"]
    role = account["role"]
    account_type = account["account-type"]
    log_messages = []
    log_messages.append(
        f"Account ID: {account_id}, Account Name: {account_name}, Role: {role}"
    )

    for region in regions:

        log_messages.append(
            f"Processing account {account_name}: {account_id} in region {region}"
        )
        try:
            if account_type in ["Hub"]:
                client = get_boto3_client(region)
            else:
                client = get_boto3_client_federated(account_id, region, role)
            status = client.get_ebs_encryption_by_default()
            log_messages.append("Checking encryption status...")
            status = status["EbsEncryptionByDefault"]

            log_messages.append(f"Status = {status}")
            response = "NA"

            if status is False:
                log_messages.append(
                    f"Enabling Default Encryption for the region: {region}"
                )
                if no_dry_run:
                    response = client.enable_ebs_encryption_by_default()[
                        "EbsEncryptionByDefault"
                    ]
                    if response:
                        log_messages.append(
                            f"Default Encryption Successfully Enabled for the region: {region}"
                        )
                    else:
                        log_messages.append(
                            f"Failed to Enable Default Encryption for the region: {region}"
                        )
                else:
                    log_messages.append("Default Encryption is not Enabled (Dry Run)")
            else:
                log_messages.append(
                    f"Default Encryption Has Already Been Enabled for the region: {region}"
                )

        except Exception as e:
            log_messages.append(
                f"WARNING: Error enabling default encryption for the region: {region}: {str(e)}"
            )

    # Log all messages at once
    logger.info("\n".join(log_messages))


def lambda_handler(event, context):
    try:
        no_dry_run = event.get("no_dry_run", False)
        s3_bucket = event.get("s3_bucket")
        s3_key = event.get("s3_key")

        if not s3_bucket or not s3_key:
            raise ValueError("S3 bucket or key not provided.")

        accounts_data = read_csv_from_s3(s3_bucket, s3_key)
        if not accounts_data:
            raise ValueError("No accounts data provided.")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(
                lambda account: ebs_default_encryption(account, no_dry_run),
                accounts_data,
            )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "EBS encryption process completed.",
                }
            ),
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": "Error processing EBS encryption.", "error": str(e)}
            ),
        }
