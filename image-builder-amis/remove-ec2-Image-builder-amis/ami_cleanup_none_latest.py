"""
ami_cleanup.py: Cleanup AWS Image Builder created AMIs in any AWS Account
"""
import sys
import time
import logging
import json
from datetime import datetime
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

# change hub name based on H1/H2/H3
hub_name = "WH-00H1"
print(hub_name)


lmb_spoke_account = {
    "WH-00H1": ["WS-Z0S4", 495416159460],
    "WH-00H2": ["WS-Y0MI", 974944152507],
    # "WH-00H3": ["WS-01AW", 768961172930],
}


def assume_role():
    source_profile = f"{hub_name}-role_OPERATIONS"
    try:
        role_arn = (
            f"arn:aws:iam::{lmb_spoke_account[hub_name][1]}:role/AWS_PLATFORM_ADMIN"
        )
        role_session_name = "DELETE-SNAPSHOT"
        session = boto3.Session(profile_name=source_profile)
        sts_client = session.client("sts")
        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
        return response["Credentials"]

    except Exception as e:
        logger.error(e)


def aws_session(region):
    credentials = assume_role()
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    )
    return session


regions = [
    "eu-west-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-southeast-3",
    "eu-central-1",
    "eu-west-2",
    "us-east-1",
    "us-east-2",
    "ca-west-1",
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


def cleanup_amis(region, cutoff_date, delete_non_latest):
    """
    Cleanup AMI
    """
    filters = [
        {
            "Name": "tag:CreatedBy",
            "Values": ["EC2 Image Builder"],
        }
    ]

    logger.info(f"Getting AMI(s) in {region} tagged as {filters}")
    try:
        all_response = (
            aws_session(region)
            .client("ec2")
            .describe_images(Owners=["self"], Filters=filters)
        )

        # Exclude images where Platform-Release is not "Latest"
        filtered_images = []

        for image in all_response["Images"]:
            # If a cutoff date is provided, filter by creation date
            if cutoff_date:
                image_creation_date = datetime.strptime(
                    image["CreationDate"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                if image_creation_date >= cutoff_date:
                    continue  # Skip this image since it doesn't meet the cutoff date

            # If the user chose to delete AMIs with no "Latest" tag, filter accordingly
            if delete_non_latest == "Y":
                if any(
                    tag.get("Key") == "Platform-Release"
                    and tag.get("Value") == "Latest"
                    for tag in image.get("Tags", [])
                ):
                    continue  # Skip this image since it has the "Latest" tag

            # Add the image to the filtered list if it meets all conditions
            filtered_images.append(image)

        # Ensure the structure of the response matches all_response
        response = {
            "Images": filtered_images,
            **{key: value for key, value in all_response.items() if key != "Images"},
        }

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
                logger.info(f"Deregistering {amis['ImageId']}")
                deregister_ami(amis["ImageId"], region)
            except ClientError as error:
                logger.error(f"Error with AMI:{amis['ImageId']}\n{error}")
            time.sleep(1)
            try:
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

    # Get user input
    cutoff_date_input = input(
        "Delete old AMIs before the cutoff date (e.g., input format 2024-6-1): (Leave blank to skip): "
    )
    delete_non_latest = input("Delete AMIs with no Latest Tag (Y/N): ").strip().upper()

    # Define cutoff date based on user input (if provided)
    cutoff_date = ""
    if cutoff_date_input:
        try:
            cutoff_date = datetime.strptime(cutoff_date_input, "%Y-%m-%d")
        except ValueError:
            logger.info("Invalid date format. Use YYYY-MM-DD.")
            cutoff_date = None
    else:
        cutoff_date = None

    input_args = [(region, cutoff_date, delete_non_latest) for region in regions]
    # Create a multiprocessing Pool with the desired number of processes
    pool = Pool(processes=len(regions))

    # Execute the process_region function in parallel for each region
    pool.starmap(cleanup_amis, input_args)

    # Close the pool to release resources
    pool.close()
    pool.join()
