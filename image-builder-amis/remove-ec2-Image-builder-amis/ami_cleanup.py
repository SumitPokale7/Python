"""
ami_cleanup.py: Cleanup AWS Image Builder created AMIs in any AWS Account
"""
import os
import sys
import time
import logging
import json

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    filename="./ami-cleanup-logfile.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))

# Global Variable
AWS_PROFILE = os.environ.get("AWS_PROFILE")


def aws_session(region):
    """
    Create AWS Session
    region: sets the aws region for boto3 session
    """
    return boto3.session.Session(region_name=region, profile_name=AWS_PROFILE)


ami_region = [
    "eu-west-1",
    "ap-northeast-2",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "eu-central-1",
    "eu-north-1",
    "eu-west-2",
    "eu-west-3",
    "us-east-1",
    "us-east-2",
    "us-west-2",
]


def get_snapid_from_ami(ebs_mapping):
    """
    Get Snapshot ID from AMI

    Parameters
    ebs_mapping: EBS Mapping
    """
    return [
        snapshot["Ebs"]["SnapshotId"] for snapshot in ebs_mapping if "Ebs" in snapshot
    ]


def deregister_ami(ami_id, region):
    """
    De-Register AMI

    Parameters
    ami_id: AMI ID
    region: AWS Region
    """
    return aws_session(region).resource("ec2").Image(ami_id).deregister()


def delete_snapshot(snapshot_id, region):
    """
    Delete Snapshot

    Parameters
    snapshot_id: EBS Snapshot ID
    region: AWS Region
    """
    for snap in snapshot_id:
        aws_session(region).resource("ec2").Snapshot(snap).delete()
    return True


def cleanup_amis():
    """
    Cleanup AMI
    """
    filters = [{"Name": "tag:CreatedBy", "Values": ["EC2 Image Builder"]}]
    for region in ami_region:
        logger.info(f"Getting AMI(s) in {region} tagged as {filters}")
        try:
            response = (
                aws_session(region)
                .client("ec2")
                .describe_images(Owners=["self"], Filters=filters)
            )
            logger.info(
                f"""Number of AMI(s) in {region}: {len(response['Images'])}\n"""
            )
            logger.debug(
                f"""Describe AMI on filters Response:
                {json.dumps(response, indent=4, default=str)}"""
            )
            for amis in response["Images"]:
                response_js = {
                    amis["ImageId"]: get_snapid_from_ami(amis["BlockDeviceMappings"])
                }
                logger.debug(
                    f"""Mapping AMI EBS Snapshot(s):
                    {json.dumps(response_js, indent=4, default=str)}\n"""
                )
                logger.info(f"Deregistering {amis['ImageId']}")
                time.sleep(3)
                try:
                    deregister_ami(amis["ImageId"], region)
                except ClientError as error:
                    logger.error(f"Error with AMI:{amis['ImageId']}\n{error}")
                logger.info(
                    f"""Deleting {amis['ImageId']}'s snapshot(s){response_js[amis['ImageId']]}"""
                )
                time.sleep(3)
                try:
                    if delete_snapshot(response_js[amis["ImageId"]], region):
                        logger.info("Operation Completed!\n")
                except ClientError as error:
                    logger.error(
                        f"Error with snapshot: {response_js[amis['ImageId']]}\n{error}"
                    )

        except Exception as err:
            logger.error(err)


cleanup_amis()
