import sys
import boto3
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    filename=f"unshare-amis-{datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")

DRY_RUN = True
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

os = [
    "WIN16",
    "WIN19",
    "WIN22",
    "RHEL7",
    "RHEL8",
    "RHELARM8",
    "SUSE12",
    "SUSE15",
]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_current_latest_amis(os, region):
    # fetch amis which are tagged with Platform-Release:Latest
    client = boto3.client("ec2", region_name=region)
    response = client.describe_images(
        Filters=[
            {
                "Name": "tag:Platform-Release",
                "Values": [
                    "Latest",
                ],
            },
            {
                "Name": "tag:BuildOS",
                "Values": [
                    os,
                ],
            },
        ],
        Owners=[
            "self",
        ],
        DryRun=False,
    )
    filtered_amis = [image for image in response.get("Images")]

    if len(filtered_amis) > 1:
        logger.warn(f"More than one Latest {os} AMI's found !!) \n")
        print("code running after warning")
    if not filtered_amis:
        raise ValueError(
            f"{len(filtered_amis)} AMIs found with Platform-Release:Latest. Should be at least one per OS"
        )
    return filtered_amis


def update_ssm_params(image_name, os):
    client = boto3.client("ssm", region_name="eu-west-1")
    if DRY_RUN:
        logger.info(f"DRY_RUN: Would have updated {os} with {image_name}")
        return

    return client.put_parameter(
        Name=f"/Ec2ImageBuilder/AMI/{os}",
        Value=image_name,
        Type="String",
        Overwrite=True,
    )


def describe_image_to_be_shared(ami_id, region):
    logger.info(f"Describing {ami_id} in {region}")
    client = boto3.client("ec2", region_name=region)
    image_metadata = client.describe_images(
        ImageIds=[
            ami_id,
        ],
        DryRun=False,
    )
    return image_metadata.get("Images")[0]


def tag_image(ami_id, os, region):
    logger.info(f"Tagging {ami_id} with {os} and Platform-Release:Latest in {region}")
    client = boto3.client("ec2", region_name=region)
    client.create_tags(
        DryRun=DRY_RUN,
        Resources=[ami_id],
        Tags=[
            {
                "Key": "Platform-Release",
                "Value": "Latest",
            },
            {
                "Key": "BuildOS",
                "Value": os,
            },
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Share AMI with other accounts")
    parser.add_argument("--ami-id", type=str, required=True, help="AMI ID to share")
    parser.add_argument(
        "--mr-kms-key-arn", type=str, required=True, help="Multi-region KMS key ARN"
    )
    parser.add_argument(
        "--org-arn", type=str, required=True, help="Org ARN which we share AMI with"
    )
    parser.add_argument(
        "--region", type=str, required=True, help="Region to share AMI with"
    )
    parser.add_argument(
        "--os",
        type=str,
        required=True,
        help="Maps to the BuildOS tag on the AMI",
        choices=[
            "WIN16",
            "WIN19",
            "WIN22",
            "RHEL7",
            "RHEL8",
            "RHELARM8",
            "SUSE12",
            "SUSE15",
        ],
    )
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
    source_ami_id = args.ami_id
    tag_image(source_ami_id, args.os, "eu-west-1")
    src_image_metadata = describe_image_to_be_shared(source_ami_id, "eu-west-1")
    update_ssm_params(src_image_metadata.get("Name"), args.os)


if __name__ == "__main__":
    main()
