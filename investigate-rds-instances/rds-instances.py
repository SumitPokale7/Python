#!/usr/bin/env python3

"""
Get a list of RDS instances linked to accounts and what they are used for in all spoke accounts.
"""
import argparse
import boto3
import csv
import json
import logging
import os
import os.path
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())

rds_client = boto3.client("rds")

rds_data_list = rds_client.describe_db_instances

TEMP_FILE = "spoke_accounts_to_process.txt"


SPOKE_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-north-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-south-1",
    "ca-central-1",
    "sa-east-1",
]


def get_boto3_client(sts_client, account_id, role_name, client_type, region):
    """Returns a boto3 client with temporary credentials for an IAM Role"""
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role_temp_credentials = get_temporary_credentials(sts_client, role_arn)
    client = boto3.client(
        client_type,
        region_name=region,
        aws_access_key_id=role_temp_credentials["AccessKeyId"],
        aws_secret_access_key=role_temp_credentials["SecretAccessKey"],
        aws_session_token=role_temp_credentials["SessionToken"],
    )
    return client


def get_temporary_credentials(sts_client, role_arn):
    """Returns a client with temporary credentials for an IAM Role"""
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="InvestigateRDSInstancesSession"
    )
    return assumed_role_object["Credentials"]


def get_spoke_account_list(org_client, hub_account_id):
    """
    Gets a list of all accounts in organization,
    with exception of Hub account ID
    """
    spoke_accounts = {}
    try:
        LOGGER.debug("Attempting to get a list of all accounts in organization")
        paginator = org_client.get_paginator("list_accounts")
        account_list = paginator.paginate().build_full_result()
        for account_item in account_list.get("Accounts"):
            spoke_account_id = account_item.get("Id")
            spoke_account_name = account_item.get("Name")
            spoke_account_status = account_item.get("Status")
            if spoke_account_id != hub_account_id:
                if spoke_account_status == "ACTIVE":
                    spoke_accounts[spoke_account_id] = spoke_account_name
        LOGGER.debug("Got a list of all accounts")
    except ClientError as exception:
        LOGGER.error("Error finding list of all accounts in organization")
        raise exception
    return spoke_accounts


def get_rds_instances(rds_client, region) -> list:
    """
    Gets a list of accounts that have RDS instances attached
    """
    try:
        LOGGER.debug("Attempting to get a list of accounts with attached RDS Instances")
        paginator = rds_client.get_paginator("describe_db_instances")
        result = paginator.paginate().build_full_result()
        LOGGER.debug("Got a list of accounts that have RDS instances attached")
        return result.get("DBInstances", [])
    except ClientError as exception:
        LOGGER.error("Error listing accounts for attached RDS instances")
        raise exception


def get_svc_ctg_product_names(svc_ctg_client):
    """Checks that the account is active"""
    product_names = []
    try:
        LOGGER.debug("Attempting to get a list of provisioned spoke accounts")
        paginator = svc_ctg_client.get_paginator("scan_provisioned_products")
        products = (
            paginator.paginate(AccessLevelFilter={"Key": "Account", "Value": "self"})
            .build_full_result()
            .get("ProvisionedProducts")
        )
        for product in products:
            product_names.append(product.get("Name"))
        LOGGER.debug("Got a list of provisioned spoke accounts")
    except ClientError as exception:
        LOGGER.error("There was and error getting provisioned spoke " "account list")
        raise exception
    return product_names


def create_report(spoke_id, spoke_name, rds_data_list):
    """
    Creates a report listing accounts, the names, number, types and raw information of RDS Instances, that certain
    RDS instance are attached to
    """
    report = []
    LOGGER.debug("Creating report for every RDS Instance.")

    for rds_data in rds_data_list:
        report.append(
            [
                spoke_id,
                spoke_name,
                rds_data["AvailabilityZone"][:-1],
                str(len(rds_data_list)),
                rds_data["DBInstanceIdentifier"],
                rds_data["DBInstanceClass"],
                str(rds_data["AllocatedStorage"]),
                rds_data["Engine"],
            ]
        )

    LOGGER.debug("Created data report.")
    return report


def read_temp_file(temp_file):
    """
    Function reads spoke accounts that need to be
    checked for db instances from a file
    """
    with open(temp_file, "r") as file:
        data_dict = json.loads(file.read())
    return data_dict


def write_temp_file(data_dict, temp_file):
    """
    Function writes spoke accounts that need to be
    checked for db instances to a file
    """
    with open(temp_file, "w") as file:
        file.write(json.dumps(data_dict))


def remove_temp_file(temp_file):
    """
    Function removes temp file that we save spoke accounts to process
    """
    os.remove(temp_file)


def print_report(report_data):
    """
    Prints report data to the console
    """
    for row in report_data:
        LOGGER.info(", ".join(row))


def write_report(rds_report_data, csv_file):
    """
    Writes the report data to a csv file
    """
    with open(csv_file, mode="a") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        for row in rds_report_data:
            report_writer.writerow(row)


def create_report_file(csv_file):
    """
    Creates csv report file with a header
    """
    with open(csv_file, mode="w") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(
            [
                "SpokeID",
                "SpokeName",
                "Region",
                "NumberOfInstances",
                "DBInstanceIdentifier",
                "DBInstanceClass",
                "AllocatedStorage",
                "Engine",
            ]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates report about RDS Instance Usage"
    )
    parser.add_argument(
        "--output-file",
        help="CSV output file, defaulted to filename: report.csv",
        default="report.csv",
    )
    parser.add_argument(
        "--role-name",
        help="Spoke account role name, defaulted to CIP_INSPECTOR",
        default="CIP_INSPECTOR",
    )
    parser.add_argument(
        "--region", help='AWS region, defaulted to "eu-west-1"', default="eu-west-1"
    )
    args = parser.parse_args()

    HUB_ACCOUNT_ID = boto3.client("sts").get_caller_identity().get("Account")
    ORG_CLIENT = boto3.client("organizations")
    STS_CLIENT = boto3.client("sts")
    SVC_CTG_CLIENT = boto3.client("servicecatalog")

    if os.path.exists(TEMP_FILE):
        SPOKE_ACCOUNTS = read_temp_file(TEMP_FILE)
    else:
        SPOKE_ACCOUNTS = get_spoke_account_list(ORG_CLIENT, HUB_ACCOUNT_ID)
        create_report_file(args.output_file)
        write_temp_file(SPOKE_ACCOUNTS, TEMP_FILE)

    SVC_CTG_PRODUCTS = get_svc_ctg_product_names(SVC_CTG_CLIENT)

    for spoke_id, spoke_name in SPOKE_ACCOUNTS.copy().items():
        if f"{spoke_name}_spoke" in SVC_CTG_PRODUCTS:
            for spoke_region in SPOKE_REGIONS:
                try:
                    RDS_CLIENT = get_boto3_client(
                        STS_CLIENT, spoke_id, args.role_name, "rds", spoke_region
                    )
                    # List all active spoke accounts in ACCOUNTS_LIST
                    ACCOUNTS_LIST = []
                    if f"{spoke_name}_spoke" not in SVC_CTG_PRODUCTS:
                        continue

                    rds_instances = get_rds_instances(RDS_CLIENT, spoke_region)
                    if not rds_instances:
                        continue
                    REPORT_ROW = create_report(spoke_id, spoke_name, rds_instances)

                except Exception as exception:
                    error_code = str(exception.response.get("Error").get("Code"))
                    if error_code == "ExpiredToken":
                        raise exception

                    REPORT_ROW = [
                        (spoke_id, spoke_name, spoke_region, "-1", error_code)
                    ]
                print_report(REPORT_ROW)
                write_report(REPORT_ROW, args.output_file)
        SPOKE_ACCOUNTS.pop(spoke_id)
        if SPOKE_ACCOUNTS:
            write_temp_file(SPOKE_ACCOUNTS, TEMP_FILE)
        else:
            remove_temp_file(TEMP_FILE)
