import logging
import boto3
import sys
from botocore.exceptions import ClientError

DRY_RUN = True
HUB_NAME = "WH-00H1"

logging.basicConfig(
    filename=f"./{HUB_NAME}-log-group-retention-update.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))


def create_session(id_, policy=None, duration=900):
    """
    Creates a session policy is an inline policy on the fly
    and passes in the session during role assumption
    :param id_: account id
    :param policy: IAM inline policy
    :param duration: IAM session duration
    :return: boto3.session
    """

    try:
        dev_session = boto3.Session(profile_name=f"{HUB_NAME}-role_SPOKE-OPERATIONS")
        target_role = f"arn:aws:iam::{id_}:role/AWS_PLATFORM_OPERATIONS"
        logger.debug(f"Assuming role: {target_role}")
        credentials = dev_session.client("sts").assume_role(
            DurationSeconds=duration,
            RoleArn=target_role,
            RoleSessionName="AssumeRole-AWS-PLATFORM_OPERATIONS"[0:64],
        )["Credentials"]
        return boto3.session.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.critical(
            {
                "Message": f"Error assuming role {target_role} ",
            }
        )
        raise e


def aws_session(service: str, region: str, spoke_account_id: str) -> object:
    """
    Creates AWS Session
    region: sets the aws region for boto3 session
    service: aws service to create boto3 client with
    spoke_account_id: customer spoke id
    """
    try:
        return create_session(spoke_account_id).client(service, region_name=region)
    except Exception as err:
        logger.info("Exception creating aws_session")
        raise ValueError(f"expecting creating AWS session, {err}")


def update_log_group_retention(account, log_group, region, dry_run):
    logs_client = aws_session("logs", region, account)
    if dry_run:
        logger.info(f"Would update {log_group} in {account} in {region}")
        response = logs_client.describe_log_groups(logGroupNamePrefix=log_group)
        for lg in response.get("logGroups"):
            if lg.get("logGroupName") == log_group:
                logger.info(
                    f"Found {log_group} in {account} in {region} with retention {lg.get('retentionInDays')}"
                )
        return
    else:
        try:
            logger.info(f"Updating {log_group} in {account} in {region}")
            logs_client.put_retention_policy(logGroupName=log_group, retentionInDays=90)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(
                    f"Log group {log_group} NOT FOUND in {account} in {region}"
                )
            else:
                logger.error(e)
    return


accounts_h1 = ["970865028323"]
accounts_h2 = ["336021475325"]
accounts_h3 = ["943415409291"]
accounts = accounts_h1
log_groups = [
    "PaloAltoCloudNGFW",
    "PaloAltoCloudNGFWAuditLog",
    "PaloAltoCloudNGFWThreatLog",
]
regions = [
    "eu-west-1",
    "us-east-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "eu-central-1",
    "eu-west-2",
]


def main(dry_run=DRY_RUN):
    for region in regions:
        for account in accounts:
            for log_group in log_groups:
                try:
                    update_log_group_retention(account, log_group, region, dry_run)
                except Exception as e:
                    logger.error(e)
                    logger.error("Error", account, log_group, region)
                    pass


if __name__ == "__main__":
    main()
