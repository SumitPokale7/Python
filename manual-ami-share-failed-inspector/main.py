from datetime import timedelta, date, datetime
import sys
import boto3
from botocore.exceptions import ClientError, WaiterError
import logging
import warnings
import argparse

logging.basicConfig(
    filename=f"unshare-amis-{datetime.now().strftime('%d-%m-%y')}.log",
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


def get_current_latest_amis(os, region="eu-west-1"):
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
        warnings.warn("Found more than one Latest AMI")
        print("code running after warning")
    if not filtered_amis:
        raise ValueError(
            f"{len(filtered_amis)} AMIs found with Platform-Release:Latest. Should be at least one per OS"
        )
    return filtered_amis


def copy_image(ami_id, mr_kms_key_arn, src_image_metadata, dest_region):
    logger.info(f"Copying {ami_id} to {dest_region}")
    client = boto3.client("ec2", region_name=dest_region)
    return client.copy_image(
        Encrypted=True,
        KmsKeyId=mr_kms_key_arn,
        Name=src_image_metadata.get("Name"),
        SourceImageId=ami_id,
        SourceRegion="eu-west-1",
        DryRun=DRY_RUN,
        CopyImageTags=True,
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


def share_image_to_org(org_arn, ami_id, region):
    client = boto3.client("ec2", region_name=region)
    try:
        logger.info(f"Sharing {ami_id} to {org_arn} in {region}")
        return client.modify_image_attribute(
            DryRun=DRY_RUN,
            ImageId=ami_id,
            LaunchPermission={
                "Add": [
                    {"OrganizationArn": org_arn},
                ]
            },
        )
    except ClientError as err:
        logger.error(f"Error setting up launch perm: for ({org_arn}) \n {err}")


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


def unshare_image_from_org(org_arn, amis, region):
    client = boto3.client("ec2", region_name=region)
    for image in amis:
        ami_id = image["ImageId"]

        try:
            logger.info(f"Unsharing {ami_id} from {org_arn} in {region}")
            return client.modify_image_attribute(
                DryRun=DRY_RUN,
                ImageId=ami_id,
                LaunchPermission={
                    "Remove": [
                        {"OrganizationArn": org_arn},
                    ]
                },
            )
        except ClientError as err:
            logger.error(f"Error removing launch perm: for ({org_arn}) \n {err}")


def update_image_tag(amis, os, region):
    unshare_date = (date.today() + timedelta(days=21)).strftime("%Y-%m-%d")
    client = boto3.client("ec2", region_name=region)
    for image in amis:
        ami_id = image["ImageId"]

        try:
            logger.info(f"Updating tags for {ami_id} in {region}")
            client.create_tags(
                DryRun=DRY_RUN,
                Resources=[ami_id],
                Tags=[
                    {
                        "Key": "Platform-Release",
                        "Value": "PendingUnshare",
                    },
                    {
                        "Key": "Unshare-Date",
                        "Value": unshare_date,
                    },
                ],
            )
        except ClientError as err:
            logger.error(f"Error updating tags for ({ami_id}) \n {err}")


def waiter(ami_id, region):
    client = boto3.client("ec2", region)
    waiter = client.get_waiter("image_available")
    waiter.config.max_attempts = 900  # Adjust the number of attempts as needed
    try:
        # Wait until the AMI copy is complete
        waiter.wait(
            Filters=[
                {"Name": "image-id", "Values": [ami_id]},
            ]
        )
        logger.info(
            f" {ami_id} of {os}: Copy operation completed successfully. in {region}"
        )
    except WaiterError as e:
        logger.error(f" Error occurred while waiting for AMI copy: {ami_id}'.format(e)")
        logger.error(e)


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
    region = args.region

    tag_image(source_ami_id, args.os, "eu-west-1")
    src_image_metadata = describe_image_to_be_shared(source_ami_id, "eu-west-1")
    # for region in ami_region:
    if region == "eu-west-1":
        logger.info(f"Skipping {region} as it is the source region")
    else:
        ami_id = copy_image(
            source_ami_id, args.mr_kms_key_arn, src_image_metadata, region
        ).get("ImageId")
        waiter(ami_id, region)
        share_image_to_org(args.org_arn, ami_id, region)
        current_latest_images = get_current_latest_amis(args.os, region)
        update_image_tag(current_latest_images, args.os, region)
        unshare_image_from_org(args.org_arn, current_latest_images, region)


if __name__ == "__main__":
    main()
