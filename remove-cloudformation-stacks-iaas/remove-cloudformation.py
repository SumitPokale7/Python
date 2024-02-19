import logging
import datetime
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    filename=f"delete-cft-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")


def delete_cft(
    client: boto3.client, stack_name: str, region: str, dry_run: bool = True
):
    """
    This methods deletes the cloudformation
    """
    try:
        if dry_run:
            logger.info(f"DRY RUN: Would have deleted cft stack { stack_name }")
            try:
                client.describe_stacks(StackName=stack_name)
            except ClientError:
                logger.warning(
                    f"Stack not found {stack_name} in region {region}, continuing"
                )
            return
        else:
            try:
                client.describe_stacks(StackName=stack_name)
            except ClientError:
                logger.warning(
                    f"Stack not found {stack_name} in region {region}, continuing"
                )
                return
            delete_cft_response = client.delete_stack(StackName=stack_name)
            waiter = client.get_waiter("stack_delete_complete")
            waiter.wait(StackName=stack_name)
            logger.info(
                f"Deleted cft stack { stack_name } delete cft response  {delete_cft_response }"
            )

    except ClientError as err:
        logger.error(f"Failed to delete the cft:\n {err}")
        raise err


def main():
    stack_names = ["CFN-SAVIYNT", "SAVIYNT-CLOUDTRAIL"]
    dry_run = True
    regions = [
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-northeast-1",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-west-1",
        "eu-central-1",
        "eu-north-1",
        "eu-west-2",
        "eu-west-3",
        "sa-east-1",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ]
    accounts = ["WE1-P2", "WU2-P2", "WE1-T1", "WU2-T1", "WE1-U1", "WU2-U1"]
    logger.info(f"Input parameters CFT_NAME : { stack_names }, regions {regions}")
    try:
        for account in accounts:
            for region in regions:
                logger.info(f"Task initiated for region { region}")
                for stack_name in stack_names:
                    stack_to_be_deleted = f"{account}-{stack_name}"
                    logger.info(
                        f" stack to be deleted {stack_to_be_deleted} for region { region} with dry run {dry_run}"
                    )
                    enterprise_profile = f"{account}-role_DEVOPS"
                    dev_session = boto3.session.Session(
                        profile_name=enterprise_profile, region_name=region
                    )
                    client = dev_session.client("cloudformation", region_name=region)
                    delete_cft(client, stack_to_be_deleted, region, dry_run)
                logger.info(f"Task finished for region { region}")
    except Exception as e:
        logger.error("An error occured: %s", str(e))


if __name__ == "__main__":
    main()
