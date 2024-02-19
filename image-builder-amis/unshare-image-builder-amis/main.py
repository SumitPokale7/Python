import os

from typing import Final
import logging
import datetime
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    filename=f"unshare-amis-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")

# protect instances
# WIN 16	EIB-ENCRYPTED-WIN16-1-2023-05-11T23-18-29.585Z
# WIN 19	EIB-ENCRYPTED-WIN19-1-2023-05-11T23-16-08.982Z
# WIN 22	EIB-ENCRYPTED-WIN22-1-2023-05-11T23-20-16.784Z
# RHEL 7	EIB-ENCRYPTED-RHEL7-1-2023-05-11T23-16-05.183Z
# RHEL 8	EIB-ENCRYPTED-RHEL8-1-2023-05-11T23-14-38.486Z
# SUSE 12	EIB-ENCRYPTED-SUSE12-1-2023-03-30T11-38-37.349Z
# SUSE 15	EIB-ENCRYPTED-SUSE15-1-2023-03-30T11-38-50.430Z
# RHEL ARM	EIB-ENCRYPTED-RHELARM8-1-2023-05-11T23-13-42.988Z


DRY_RUN: Final = False
PROFILE = "WH-00H1-role_SPOKE-OPERATIONS"
ACCOUNT_ID: Final = os.getenv("ACCOUNT_ID", "495416159460")  # H1
# ACCOUNT_ID: Final = os.getenv("ACCOUNT_ID", "974944152507") # H2
# ACCOUNT_ID: Final = os.getenv("ACCOUNT_ID", "768961172930") # H3

protected_instances = [
    "EIB-ENCRYPTED-WIN16-1-2023-05-11T23-18-29.585Z",
    "EIB-ENCRYPTED-WIN19-1-2023-05-11T23-16-08.982Z",
    "EIB-ENCRYPTED-WIN22-1-2023-05-11T23-20-16.784Z",
    "EIB-ENCRYPTED-RHEL7-1-2023-05-11T23-16-05.183Z",
    "EIB-ENCRYPTED-RHEL8-1-2023-05-11T23-14-38.486Z",
    "EIB-ENCRYPTED-SUSE12-1-2023-03-30T11-38-37.349Z",
    "EIB-ENCRYPTED-SUSE15-1-2023-03-30T11-38-50.430Z",
    "EIB-ENCRYPTED-RHELARM8-1-2023-05-11T23-13-42.988Z",
]


def protected_instance(ami):
    if ami["Name"] in protected_instances:
        logger.warning(f"Protected Instance: {ami['Name']}")
        return True
    return False


def create_creds(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="LambdaInventorySession"
    )


def create_client(
    service: str, role: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        creds = create_creds(role, hub_session)
        client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"cannot assume the role: {e}")
        raise e

    return client


def create_resource(
    service: str, role: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        creds = create_creds(role, hub_session)
        resource = boto3.resource(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"cannot assume the role: {e}")
        raise e

    return resource


def unshare_amis(region: str, dry_run: bool = True):
    filters = [
        {
            "Name": "tag:Platform-Release",
            "Values": ["PendingUnshare"],
        },
    ]

    try:
        session = boto3.session.Session(profile_name=PROFILE, region_name=region)
        ec2_client = create_client(
            "ec2",
            f"arn:aws:iam::{ACCOUNT_ID}:role/AWS_PLATFORM_OPERATIONS",
            region,
            session,
        )
        ec2_resource = create_resource(
            "ec2",
            f"arn:aws:iam::{ACCOUNT_ID}:role/AWS_PLATFORM_OPERATIONS",
            region,
            session,
        )
        paginator = ec2_client.get_paginator("describe_images")
        response_iterator = paginator.paginate(
            Filters=filters, Owners=["self"], PaginationConfig={"PageSize": 10}
        )
        for response in response_iterator:
            for ami in response["Images"]:
                if not protected_instance(ami):
                    unshare_ami(ami, ec2_resource, dry_run)
    except ClientError as err:
        logger.error(f"Error getting ami's tagged PendingUnshare:\n {err}")
        raise err


def get_ami_id_launchpermissions(ec2_resource, ami_id):
    try:
        response = ec2_resource.Image(ami_id).describe_attribute(
            Attribute="launchPermission"
        )
    except ClientError as err:
        logger.error(f"Error getting ami's ({ami_id}) launch perm:\n {err}")
        raise err
    if response["LaunchPermissions"] != []:
        for org in response["LaunchPermissions"]:
            if "OrganizationArn" in org:
                return org["OrganizationArn"]
            if "UserId" in org:
                logger.warning(
                    f"{ami_id} has launch permissions, UserId: {org['UserId']}"
                )
    return ""


def unshare_ami(ami, ec2_resource, dry_run: bool = True):
    orgArn = get_ami_id_launchpermissions(ec2_resource, ami["ImageId"])
    launchpermission = {
        "Remove": [
            {
                "OrganizationArn": orgArn,
            },
        ]
    }
    try:
        response = {}
        if orgArn != "":
            if dry_run:
                logger.info(
                    f"Would have removed AMI Launch Permission for {ami['ImageId']}"
                )
                response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            else:
                logger.info("remove launch permission")
                response = ec2_resource.Image(ami["ImageId"]).modify_attribute(
                    Attribute="launchPermission",
                    LaunchPermission=launchpermission,
                    OperationType="remove",
                )
        if orgArn == "" or response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            if dry_run:
                logger.info(
                    f"Would have updated tag for {ami['ImageId']}, created date {ami['CreationDate']}"
                )
            else:
                logger.info("update tag")
                logger.info(
                    f'Removed AMI Launch Permission for {ami["ImageId"]}, created date {ami["CreationDate"]}'
                )
                update_tags = {"Key": "Platform-Release", "Value": "Unshared"}
                ami["Tags"] = ec2_resource.Image(ami["ImageId"]).create_tags(
                    Tags=[update_tags]
                )
                logger.info(
                    f"UpdateTag AMI: {ami['ImageId']} with {update_tags['Key']}:{update_tags['Value']}"
                )

    except ClientError as err:
        logger.error(f"Error:\n {err}")


if __name__ == "__main__":
    # regions = [
    #     "us-east-1",
    #     "ap-northeast-2",
    #     "ap-south-1",
    #     "ap-southeast-1",
    #     "ap-southeast-2",
    #     "eu-central-1",
    #     "eu-north-1",
    #     "eu-west-2",
    #     "eu-west-3",
    #     "us-east-1",
    #     "us-east-2",
    #     "us-west-2"
    # ]
    regions = ["eu-west-1"]
    for region in regions:
        unshare_amis(region, dry_run=DRY_RUN)
