from argparse import ArgumentParser
import csv
import datetime
import boto3
import logging
import pandas as pd
import concurrent.futures
import botocore.exceptions

logger = logging.getLogger(__name__)


def config_log():
    file_name = f"./noncore_ebs_encryption_logfile {datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"
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


def get_all_active_account_ids(excel_file):
    df = pd.read_csv(excel_file)
    accounts = df.to_dict(orient="records")
    logger.info(f"{len(accounts)} active accounts found in the Excel file.")
    logger.info(accounts)
    logger.debug(accounts)
    return accounts


def get_boto3_client_enterprise(region, role):
    PROFILE = role
    try:
        dev_session = boto3.session.Session(profile_name=PROFILE, region_name=region)
    except botocore.exceptions.ProfileNotFound:
        dev_session = boto3.session.Session(profile_name=PROFILE, region_name=region)

    logger.info(f"profile name: {PROFILE}")
    return dev_session.client("ec2")


def ebs_default_encryption(account, no_dry_run):
    """
    Enables EBS encryption by default for all instances
    """
    print(account)
    account_id = account["account-id"]
    account_name = account["account-name"]
    role = account["role"]
    logger.info(f"Account ID: {account_id}, Account Name: {account_name}, Role: {role}")
    log_messages = []
    processed_list_individual = []
    for region in regions:
        log_messages.append(
            f"Processing account {account_name}: {account_id} in region {region}"
        )
        try:

            client = get_boto3_client_enterprise(region, role)
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
    parser.add_argument("--no-dry-run", help="Dry run", action="store_true")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to the Excel file containing account details",
        required=True,
    )

    args = parser.parse_args()
    logger = config_log()
    logger.info(f"No Dry Run : {args.no_dry_run}")
    accounts = get_all_active_account_ids(args.file)
    print(accounts)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(
            lambda account: ebs_default_encryption(account, args.no_dry_run), accounts
        )
    date_time = datetime.datetime.now()
    _format = "%Y-%m-%d-%H-%M-%S"
    with open(
        f'noncore_ebs_encryption_{date_time.strftime(_format)}_{"" if args.no_dry_run else "not_"}processed.csv',
        "w",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerows(processed_list)
# 837302091737,WE1-A1 ALPHA,Enterprise,Production,WE1-A1-role_DEVOPS
# 881091386611,WU2-A1 ALPHA,Enterprise,Production,WU2-A1-role_DEVOPS
