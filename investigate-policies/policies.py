"""
Get a list of roles that have certain policies attached in all spoke accounts
"""

import csv
import logging
import argparse
from random import randint
from time import sleep
import boto3
from botocore.exceptions import ClientError


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


# Define required policies in the list below
POLICY_ARNS = [
    "arn:aws:iam::aws:policy/AdministratorAccess",
    "arn:aws:iam::aws:policy/PowerUserAccess",
]
# Nothing should be changed below this line


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
        RoleArn=role_arn, RoleSessionName="InvestigatePoliciesSession"
    )
    return assumed_role_object["Credentials"]


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


def get_spoke_account_list(hub_account_id, org_client):
    """
    Gets a list of all accounts in organization,
    with exception of Hub account ID
    """
    spoke_accounts = {}
    try:
        LOGGER.debug("Attemptng to get a list of all accounts in organization")
        paginator = org_client.get_paginator("list_accounts")
        account_list = paginator.paginate().build_full_result()
        for account_item in account_list.get("Accounts"):
            spoke_account_id = account_item.get("Id")
            spoke_account_name = account_item.get("Name")
            spoke_account_status = account_item.get("Status")
            if spoke_account_id != hub_account_id:
                if spoke_account_status == "ACTIVE":
                    spoke_accounts[spoke_account_id] = spoke_account_name
        LOGGER.debug("Got a list of all accounts.")
    except ClientError as exception:
        LOGGER.error("Error finding list of all accounts in organization")
        raise exception
    return spoke_accounts


def get_list_of_entities_for_policy(iam_client, iam_policy_arn):
    """
    Gets a list of entities that have the policy attached
    Thius is to do with the policy passed as an arument to this function
    """
    entities_dict = {}
    try:
        LOGGER.debug(
            "Attempting to get a list of roles for " f"policy '{iam_policy_arn}'"
        )
        paginator = iam_client.get_paginator("list_entities_for_policy")
        entities_list = paginator.paginate(
            PolicyArn=iam_policy_arn,
        ).build_full_result()
        entities_dict[iam_policy_arn] = entities_list
        LOGGER.debug(f"Got a list of roles for policy '{iam_policy_arn}'")
    except ClientError as exception:
        LOGGER.error("Error listing roles for policy")
        raise exception
    return entities_dict


def create_report(spoke_id, spoke_name, entities_list):
    """
    Creates a list of lists report of users, groups and roles that certain
    policy is attached to
    """
    report = []
    LOGGER.debug("Creating report for every spoke account.")
    # AccountId | AccountName | AWSPolicy | ResourceType (User,Role,Group) ->
    # | ResourceArn
    for policy_data in entities_list:
        for policy_arn, entities_attached in policy_data.items():
            roles = entities_attached.get("PolicyRoles")
            if roles:
                for role in roles:
                    role_name = role.get("RoleName")
                    report.append(
                        [
                            spoke_id,
                            spoke_name,
                            policy_arn,
                            "IAM Role",
                            f"arn:aws:iam::{spoke_id}:role/{role_name}",
                        ]
                    )
            users = entities_attached.get("PolicyUsers")
            if users:
                for user in users:
                    user_name = user.get("UserName")
                    report.append(
                        [
                            spoke_id,
                            spoke_name,
                            policy_arn,
                            "IAM User",
                            f"arn:aws:iam::{spoke_id}:user/{user_name}",
                        ]
                    )
            groups = entities_attached.get("PolicyGroups")
            if groups:
                for group in groups:
                    group_name = group.get("GroupName")
                    report.append(
                        [
                            spoke_id,
                            spoke_name,
                            policy_arn,
                            "IAM Group",
                            f"arn:aws:iam::{spoke_id}:group/{group_name}",
                        ]
                    )
    LOGGER.debug("Created data report.")
    return report


def create_report_file(csv_file):
    """
    Creates csv report file with a header
    """
    with open(csv_file, mode="w") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(
            ["AccountId", "AccountName", "AWSPolicy", "ResourceType", "ResourceArn"]
        )


def print_report(report_data):
    """
    Prints report data to the console
    """
    for row in report_data:
        LOGGER.info(", ".join(row))


def write_report(report_data, csv_file):
    """
    Writes report data to a csv file
    """
    with open(csv_file, mode="a") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        for row in report_data:
            report_writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates report about policies usage")
    parser.add_argument(
        "--output-file",
        help="CSV output file, defaults to filename: report.csv",
        default="report.csv",
    )
    parser.add_argument(
        "--role-name",
        help="Spoke account role name, defaults to CIP_INSPECTOR",
        default="CIP_INSPECTOR",
    )
    parser.add_argument(
        "--region", help='AWS region, defaults to "eu-west-1"', default="eu-west-1"
    )

    args = parser.parse_args()

    HUB_ACCOUNT_ID = boto3.client("sts").get_caller_identity().get("Account")
    SVC_CTG_CLIENT = boto3.client("servicecatalog")
    ORG_CLIENT = boto3.client("organizations")
    STS_CLIENT = boto3.client("sts")

    create_report_file(args.output_file)

    SVC_CTG_PRODUCTS = get_svc_ctg_product_names(SVC_CTG_CLIENT)

    SPOKE_ACCOUNTS = get_spoke_account_list(HUB_ACCOUNT_ID, ORG_CLIENT)

    for spoke_id, spoke_name in SPOKE_ACCOUNTS.items():
        try:
            sleep(randint(1, 10))

            if f"{spoke_name}_spoke" in SVC_CTG_PRODUCTS:
                IAM_CLIENT = get_boto3_client(
                    STS_CLIENT, spoke_id, args.role_name, "iam", args.region
                )
                ENTITIES_LIST = []

                for policy_arn in POLICY_ARNS:
                    ENTITIES_LIST.append(
                        get_list_of_entities_for_policy(IAM_CLIENT, policy_arn)
                    )

                REPORT_DATA = create_report(spoke_id, spoke_name, ENTITIES_LIST)

                print_report(REPORT_DATA)

                write_report(REPORT_DATA, args.output_file)
        except Exception as exception:
            error_code = str(exception.response.get("Error").get("Code"))
            if error_code == "ExpiredToken":
                raise exception
            REPORT_ROW = [(spoke_id, spoke_name, error_code, "*", "*")]
            print_report(REPORT_ROW)
            write_report(REPORT_ROW, args.output_file)
