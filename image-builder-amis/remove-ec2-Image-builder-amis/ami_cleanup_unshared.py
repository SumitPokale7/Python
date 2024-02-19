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
from multiprocessing import Pool

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

regions = [
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


def aws_session(region):
    """
    Create AWS Session
    region: sets the aws region for boto3 session
    """
    return boto3.session.Session(region_name=region, profile_name=AWS_PROFILE)


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


def deprecate_ami(ami_id, region):
    """
    Add Depricated Tag only for eu-west-1

    Parameters
    ami_id: AMI ID
    """
    update_tags = {"Key": "Platform-Release", "Value": "Deprecated"}
    return (
        aws_session(region)
        .resource("ec2")
        .Image(ami_id)
        .create_tags(Tags=[update_tags])
    )


def cleanup_amis(region):
    """
    Cleanup AMI
    """
    filters = [
        {
            "Name": "tag:CreatedBy",
            "Values": ["EC2 Image Builder"],
        },
        {
            "Name": "tag:Platform-Release",
            "Values": ["Unshared"],
        }
    ]

    logger.info(f"Getting AMI(s) in {region} tagged as {filters}")
    try:
        response = (
            aws_session(region)
            .client("ec2")
            .describe_images(Owners=["self"], Filters=filters)
        )
        logger.info(f"""Number of AMI(s) in {region}: {len(response['Images'])}\n""")
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
            time.sleep(1)
            try:
                if region == "eu-west-1":
                    logger.info(f"Add Deprecate tag to {amis['ImageId']}")
                    deprecate_ami(amis["ImageId"], "eu-west-1")
                else:
                    logger.info(f"Deregistering {amis['ImageId']}")
                    deregister_ami(amis["ImageId"], region)
            except ClientError as error:
                logger.error(f"Error with AMI:{amis['ImageId']}\n{error}")
            time.sleep(1)
            try:
                if region != "eu-west-1":
                    if delete_snapshot(response_js[amis["ImageId"]], region):
                        logger.info("Snapshote delete operation Completed!\n")
            except ClientError as error:
                logger.error(
                    f"Error with snapshot: {response_js[amis['ImageId']]}\n{error}"
                )

    except Exception as err:
        logger.error(err)


if __name__ == "__main__":
    # Add the regions you want to process

    # Create a multiprocessing Pool with the desired number of processes
    pool = Pool(processes=len(regions))

    # Execute the process_region function in parallel for each region
    pool.map(cleanup_amis, regions)

    # Close the pool to release resources
    pool.close()
    pool.join()
