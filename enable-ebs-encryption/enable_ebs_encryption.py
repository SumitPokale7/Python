from argparse import ArgumentParser
import csv
import datetime
import boto3
from boto3.dynamodb.conditions import Attr
import logging
from hs_service.aws.dynamodb import DynamoDB
import concurrent.futures

logger = logging.getLogger(__name__)


def config_log(hub_env):
    file_name = f"./{hub_env}_ebs_encryption_logfile {datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"
    logging.basicConfig(
        filename=file_name,
        filemode="a",
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
        level="INFO",
    )
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger()


regions = [
    "eu-west-2",
    "us-east-2",
    "ap-southeast-2",
    "eu-central-1",
    "ap-southeast-1",
    "eu-west-1",
    "ap-southeast-3",
    "ca-west-1",
    "us-east-1",
]
processed_list = [
    [
        "account-id",
        "account-name",
        "region",
        "dry-run",
        "ebs_encryption_status_before",
        "ebs_encryption_status_after",
    ]
]


def get_all_active_account_ids(hub_env):
    filter_expression = Attr("status").eq("Active") & Attr("account-type").ne("Hub")
    dynamodb = DynamoDB(f"{hub_env}-DYN_METADATA")
    results = dynamodb.get_all_entries(filter_expression=filter_expression)

    logger.info(f"{len(results)} active accounts found in DDB matadata table.")
    logger.debug(results)
    return results


def get_boto3_client(account_id, client_type, region):
    role_temp_credentials = get_temporary_credentials(account_id)
    ec2_client = boto3.client(
        client_type,
        aws_access_key_id=role_temp_credentials["AccessKeyId"],
        aws_secret_access_key=role_temp_credentials["SecretAccessKey"],
        aws_session_token=role_temp_credentials["SessionToken"],
        region_name=region,
    )
    return ec2_client


def get_temporary_credentials(account_id):
    sts_client = boto3.client("sts")
    role_arn = f"arn:aws:iam::{account_id}:role/AWS_PLATFORM_ADMIN"
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="EnablingEBSDefaultEncryption"
    )

    logger.debug(f'Returning temporary credentials for "{role_arn}"')
    return assumed_role_object["Credentials"]


def ebs_default_encryption(account, no_dry_run):
    """
    Enables EBS encryption by default for all instances
    """
    account_id = account["account"]
    account_name = account["account-name"]
    log_messages = []
    processed_list_individual = []
    for region in regions:
        log_messages.append(
            f"Processing account {account_name}: {account_id} in region {region}"
        )

        try:
            client = get_boto3_client(account_id, "ec2", region)
            status = client.get_ebs_encryption_by_default()
            log_messages.append("Checking encryption status...")
            status = status["EbsEncryptionByDefault"]
            log_messages.append(f"Status = {status}")
            response = "NA"
            if status is False:
                log_messages.append(
                    f"Enabling Default Encryption for the region: {region}"
                )
                if no_dry_run:
                    response = client.enable_ebs_encryption_by_default()[
                        "EbsEncryptionByDefault"
                    ]
                    log_messages.append(
                        f"Default Encryption Successfully Enabled for the region: {region}"
                    )
                else:
                    log_messages.append("Default Encryption is not Enabled (Dry Run)")
            else:
                log_messages.append(
                    f"Default Encryption Has Already Been Enabled for the region: {region}"
                )
            processed_list_individual.append(
                [account_id, account_name, region, not no_dry_run, status, response]
            )
        except Exception as e:
            log_messages.append(
                f"WARNING: Error enabling default encryption for the region: {region}: {str(e)}"
            )
    processed_list.extend(processed_list_individual)
    # Log all messages at once

    logger.info("\n".join(log_messages))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-e",
        "--hub_env",
        type=str,
        help="Provide hub name example: WH-0002",
        required=True,
    )
    parser.add_argument("--no-dry-run", help="Dry run", action="store_true")

    args = parser.parse_args()
    logger = config_log(args.hub_env)
    logger.info(f"No Dry Run : {args.no_dry_run}")
    logger.info(f"Hub Environment : {args.hub_env}")
    accounts = get_all_active_account_ids(args.hub_env)
    hub_account_id = boto3.client("sts").get_caller_identity().get("Account")
    accounts.append(
        {"account": hub_account_id, "account-name": args.hub_env, "account-type": "Hub"}
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(
            lambda account: ebs_default_encryption(account, args.no_dry_run), accounts
        )
    date_time = datetime.datetime.now()
    _format = "%Y-%m-%d-%H-%M-%S"
    with open(
        f'{args.hub_env}_ebs_encryption_{date_time.strftime(_format)}_{"" if args.no_dry_run else "not_"}processed.csv',
        "w",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerows(processed_list)
