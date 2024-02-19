import logging
import datetime
import boto3
from botocore.exceptions import ClientError
import argparse

logging.basicConfig(
    filename=f"delete-cft-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")


def assume_role(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="CFT-Delete-Activity-Session"
    )


def create_client(service: str, role: str, region: str, aws_profile: str):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        session = boto3.session.Session(profile_name=aws_profile, region_name=region)
        creds = assume_role(role, session)
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


def delete_cft(
    region: str,
    CFT_TO_BE_DELETED: str,
    AWS_PROFILE: str,
    API_ACCOUNT_ID: str,
    ROLE_NAME: str,
):
    """
    This methods deletes the cloudformation for a specified region
    """
    try:
        cft_client = create_client(
            "cloudformation",
            f"arn:aws:iam::{API_ACCOUNT_ID}:role/{ROLE_NAME}",
            region,
            AWS_PROFILE,
        )
        # Deleting CFT
        delete_cft_response = cft_client.delete_stack(StackName=CFT_TO_BE_DELETED)
        logger.info(
            f"Deleted cft stack { CFT_TO_BE_DELETED } region { region } delete cft response  {delete_cft_response }"
        )

    except ClientError as err:
        logger.error(f"Failed to delete the cft:\n {err}")
        raise err


def main():
    # Accepting CLI args
    parser = argparse.ArgumentParser()
    parser.add_argument("--cft-to-be-deleted", help="", type=str)
    parser.add_argument("--regions", help="", type=str)
    parser.add_argument("--aws-profile", help="", type=str)
    parser.add_argument("--api-account-id", type=str)
    parser.add_argument("--role-name", type=str)
    args = parser.parse_args()

    # Assigning CLI args to internal vars
    CFT_TO_BE_DELETED = args.cft_to_be_deleted
    REGIONS = args.regions.split(",")
    AWS_PROFILE = args.aws_profile
    API_ACCOUNT_ID = args.api_account_id
    ROLE_NAME = args.role_name

    logger.info(
        f"Input parameters CFT_NAME : { CFT_TO_BE_DELETED }, regions {REGIONS}, PROFILE { AWS_PROFILE }, API_ACCOUNT_ID { API_ACCOUNT_ID },  ROLE_NAME {ROLE_NAME}"
    )
    try:
        for region in REGIONS:
            logger.info(f"Task initiated for region { region}")
            logger.info(f"Deleting cft {CFT_TO_BE_DELETED} for region { region}")
            delete_cft(
                region=region,
                CFT_TO_BE_DELETED=CFT_TO_BE_DELETED,
                AWS_PROFILE=AWS_PROFILE,
                API_ACCOUNT_ID=API_ACCOUNT_ID,
                ROLE_NAME=ROLE_NAME,
            )
            logger.info(f"Task finished for region { region}")
    except Exception as e:
        logger.error("An error occured: %s", str(e))


if __name__ == "__main__":
    main()
