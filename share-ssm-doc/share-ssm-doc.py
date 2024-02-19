from argparse import ArgumentParser
import datetime
import logging
import json
import sys
import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from hs_service.aws.dynamodb import DynamoDB

hub_name = ""
lmb_spoke_account = {
    "WH-0001": ["Z0S4", 495416159460],
    "WH-0002": ["Y0MI", 974944152507],
    "WH-0003": ["01AW", 768961172930],
}

file_name = f"./share-ssm-doc-logfile {datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"
logging.basicConfig(
    filename=file_name,
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))
BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


def fetch_accounts_from_metadata(hub_name):
    logger.info(f"Fetching spoke accounts from table {hub_name}-DYN_METADATA")
    dynamodb = DynamoDB(f"{hub_name}-DYN_METADATA")

    filter_expression = (
        Attr("status").eq("Active")
        & Attr("account-type").ne("Hub")
        & Attr("account-type").ne("Security")
    )

    return dynamodb.get_all_entries(filter_expression=filter_expression)


# Assume AWS_PLATFORM_ADMIN Role in respective image builder spoke account
def assume_role():
    try:
        role_arn = (
            f"arn:aws:iam::{lmb_spoke_account[hub_name][1]}:role/AWS_PLATFORM_ADMIN"
        )
        role_session_name = "SHARE-SSM-DOC"
        sts_client = boto3.client("sts")
        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
        return response["Credentials"]

    except Exception as e:
        logger.error(e)


def invoke_ssm_lambda(spoke_id, region, dry_run):
    credentials = assume_role()
    client = boto3.client(
        "lambda",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name="eu-west-1",
    )

    lambda_name = f"arn:aws:lambda:eu-west-1:{lmb_spoke_account[hub_name][1]}:function:WS-{lmb_spoke_account[hub_name][0]}-LMB_SSM-DOCUMENT-SHARING"
    payload = json.dumps(
        {
            "Records": [
                {
                    "Sns": {
                        "TopicArn": "SSM-SPOKE-Creation",
                        "Message": json.dumps(
                            {"SpokeAccountId": spoke_id, "Region": region}
                        ),
                    },
                }
            ]
        }
    )

    logger.info(f"Payload {payload}")

    invocation_type = "DryRun" if dry_run else "Event"
    client.invoke(
        FunctionName=lambda_name,
        InvocationType=invocation_type,
        Payload=payload,
    )
    logger.info("Shared ssm document Succesfully")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-e",
        "--hub_env",
        type=str,
        help="Provide hub name example: WH-0002",
        required=True,
    )
    parser.add_argument("--no-dry-run", help="Dry run", action="store_false")
    args = parser.parse_args()

    hub_name = args.hub_env
    logger.info(f"Dry Run : {args.no_dry_run}")
    response = fetch_accounts_from_metadata(hub_name)
    for item in response:
        if "region" in item:
            logger.info(f"Triggering SSM Document Sharing For {item['account-name']}")
            invoke_ssm_lambda(item["account"], item["region"], args.no_dry_run)
        else:
            logger.warning(f"account {item['account']} has no region")
