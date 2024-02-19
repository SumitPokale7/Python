"""[H&S] Investigate who uses public AMIs in Federated Accounts"""

import logging as logger
from random import randint
from time import sleep
import os
import os.path
import json
import argparse
import csv
import boto3
from botocore.exceptions import ClientError


logger.basicConfig(level=logger.INFO)


# Regions and temp file variables
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
# Nothing should be changed below this line


def get_spoke_account_list(org_client, hub_account_id):
    """
    Function to get spoke account list from the AWS Organizations
    """
    spoke_accounts = {}
    try:
        paginator = org_client.get_paginator("list_accounts")
        account_info = paginator.paginate().build_full_result().get("Accounts")
        for spoke_account in account_info:
            spoke_account_id = spoke_account.get("Id")
            spoke_account_name = spoke_account.get("Name")
            spoke_account_status = spoke_account.get("Status")
            if spoke_account_id != hub_account_id:
                if spoke_account_status == "ACTIVE":
                    spoke_accounts[spoke_account_id] = spoke_account_name
    except ClientError as exception:
        logger.error("Failed to get spoke account list")
        raise exception
    return spoke_accounts


def get_ou_name(org_client, ou_id):
    """Get AWS Organizational Unit name given OU ID"""
    ou_name = ""
    try:
        ou_name = (
            org_client.describe_organizational_unit(OrganizationalUnitId=ou_id)
            .get("OrganizationalUnit")
            .get("Name")
        )
    except ClientError as exception:
        logger.error("Failed to get OU name")
        raise exception
    return ou_name


def get_parent_name(org_client, spoke_account_id):
    """
    Function gets parent OU ID for every spoke account
    """
    parent_name = ""
    try:
        paginator = org_client.get_paginator("list_parents")
        parents = (
            paginator.paginate(ChildId=spoke_account_id)
            .build_full_result()
            .get("Parents")
        )
        parent_id = parents[0].get("Id")
        parent_type = parents[0].get("Type")
        if parent_type == "ORGANIZATIONAL_UNIT":
            parent_name = get_ou_name(org_client, parent_id)
    except ClientError as exception:
        logger.error("Failed to get parent ID for account")
        raise exception
    return parent_name


def get_svc_ctg_product_names(svc_ctg_client):
    """
    Function to checks that the account is active.
    """
    product_names = []
    try:
        paginator = svc_ctg_client.get_paginator("scan_provisioned_products")
        products = (
            paginator.paginate(AccessLevelFilter={"Key": "Account", "Value": "self"})
            .build_full_result()
            .get("ProvisionedProducts")
        )
        for product in products:
            product_names.append(product.get("Name"))
    except ClientError as exception:
        logger.error("There was an error getting provisioned spoke " "account list")
        raise exception
    return product_names


def get_boto3_client(sts_client, account_id, role_name, client_type, region):
    """
    Function returns a boto3 client with temporary credentials for an
    IAM Role
    """
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


def get_boto3_resource(sts_client, account_id, role_name, resource_type, region):
    """
    Function returns a boto3 resource with temporary credentials for an
    IAM Role
    """
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role_temp_credentials = get_temporary_credentials(sts_client, role_arn)
    resource = boto3.resource(
        resource_type,
        region_name=region,
        aws_access_key_id=role_temp_credentials["AccessKeyId"],
        aws_secret_access_key=role_temp_credentials["SecretAccessKey"],
        aws_session_token=role_temp_credentials["SessionToken"],
    )
    return resource


def get_temporary_credentials(sts_client, role_arn):
    """
    Function returns a client with temporary credentials for an IAM Role
    """
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="InvestigateImagesSession"
    )
    return assumed_role_object["Credentials"]


def get_instance_and_ami_ids(ec2_client):
    """
    Function gets a list of instances in the account and specific region
    """
    instance_ami_list = []
    try:
        paginator = ec2_client.get_paginator("describe_instances")
        reservation_info = paginator.paginate().build_full_result().get("Reservations")
        if reservation_info:
            for reservation in reservation_info:
                list_of_instances = reservation.get("Instances")
                for instance in list_of_instances:
                    instances = {}
                    instances["image_id"] = instance.get("ImageId")
                    instances["instance_id"] = instance.get("InstanceId")
                    instance_ami_list.append(instances)
    except ClientError as exception:
        logger.error("Failed to get instance list")
        raise exception
    return instance_ami_list


def create_report(
    instance_list, ou_name, account_id, account_name, spoke_region, ec2_resource
):
    """
    Function creates a report about instances using public images
    """
    required_instance_data = []
    for instance in instance_list:
        image_data = {}
        image_id = instance["image_id"]
        instance_id = instance["instance_id"]
        image_data = query_image(image_id, ec2_resource)
        if image_data["public"] is True or image_data["public"] == "No data":
            image_data["ou_name"] = ou_name
            image_data["account_id"] = account_id
            image_data["account_name"] = account_name
            image_data["spoke_region"] = spoke_region
            image_data["instance_id"] = instance_id
            required_instance_data.append(image_data)
    return required_instance_data


def query_image(image_id, ec2_resource):
    """
    Function queries images to get extra info about each image
    """
    image_data = {}
    img = ec2_resource.Image(image_id)
    try:
        image_data = dict(
            image_id=img.image_id,
            image_platform=img.platform,
            platform_details=img.platform_details,
            owner_id=img.owner_id,
            public=img.public,
            image_owner_alias=img.image_owner_alias,
            description=img.description,
            image_type=img.image_type,
        )
    except Exception:
        image_data = dict(
            image_id=image_id,
            image_platform="No data",
            platform_details="No data",
            owner_id="No data",
            public="No data",
            image_owner_alias="No data",
            description="No data",
            image_type="No data",
        )
    return image_data


def read_temp_file(temp_file):
    """
    Function reads spoke accounts that need to be
    checked for instances from a file
    """
    with open(temp_file, "r") as file:
        data_dict = json.loads(file.read())
    return data_dict


def write_temp_file(data_dict, temp_file):
    """
    Function writes spoke accounts that need to be
    checked for instances to a file
    """
    with open(temp_file, "w") as file:
        file.write(json.dumps(data_dict))


def remove_temp_file(temp_file):
    """
    Function removes temp file that we save spoke accounts to process
    """
    os.remove(temp_file)


def create_csv(csv_file):
    """
    Creates csv report file with a header
    """
    with open(csv_file, mode="w") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(
            [
                "ou_name",
                "account_id",
                "account_name",
                "region",
                "instance_id",
                "image_id",
                "image_platform",
                "platform_details",
                "public",
                "owner_id",
                "image_owner_alias",
                "description",
                "image_type",
            ]
        )


def print_header_to_the_console():
    """
    Function prints header to the console
    """
    header = [
        "ou_name",
        "account_id",
        "account_name",
        "region",
        "instance_id",
        "image_id",
        "image_platform",
        "platform_details",
        "public",
        "owner_id",
        "image_owner_alias",
        "description",
        "image_type",
    ]
    print(", ".join(header))


def print_to_console(result):
    """
    Function to print report to the console
    """
    if result:
        for item in result:
            row = [
                item["ou_name"] or "",
                item["account_id"] or "",
                item["account_name"] or "",
                item["spoke_region"] or "",
                item["instance_id"] or "",
                item["image_id"] or "",
                item["image_platform"] or "",
                item["platform_details"] or "",
                str(item["public"]) or "",
                item["owner_id"] or "",
                item["image_owner_alias"] or "",
                item["description"] or "",
                item["image_type"] or "",
            ]
            print(", ".join(row))


def add_info_to_csv_file(result, csv_file):
    """
    Function to write output into a .csv file
    """
    if result:
        with open(csv_file, "a") as csvfile:
            report_writer = csv.writer(
                csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            for item in result:
                report_writer.writerow(
                    [
                        item["ou_name"],
                        item["account_id"],
                        item["account_name"],
                        item["spoke_region"],
                        item["instance_id"],
                        item["image_id"],
                        item["image_platform"],
                        item["platform_details"],
                        item["public"],
                        item["owner_id"],
                        item["image_owner_alias"],
                        item["description"],
                        item["image_type"],
                    ]
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates report about public image usage"
    )
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
    args = parser.parse_args()

    HUB_ACCOUNT_ID = boto3.client("sts").get_caller_identity().get("Account")
    STS_CLIENT = boto3.client("sts")
    ORG_CLIENT = boto3.client("organizations")
    SVC_CTG_CLIENT = boto3.client("servicecatalog")
    print_header_to_the_console()
    if os.path.exists(TEMP_FILE):
        SPOKE_ACCOUNTS = read_temp_file(TEMP_FILE)
    else:
        SPOKE_ACCOUNTS = get_spoke_account_list(ORG_CLIENT, HUB_ACCOUNT_ID)
        create_csv(args.output_file)
    REMAINING_ACCOUNTS = dict(SPOKE_ACCOUNTS)
    write_temp_file(REMAINING_ACCOUNTS, TEMP_FILE)
    SVC_CTG_PRODUCTS = get_svc_ctg_product_names(SVC_CTG_CLIENT)
    for account_id, account_name in SPOKE_ACCOUNTS.items():
        sleep(randint(1, 10))
        ou_name = ""
        svc_acc_name = f"{account_name}_spoke"
        if svc_acc_name in SVC_CTG_PRODUCTS:
            ou_name = get_parent_name(ORG_CLIENT, account_id)
            for spoke_region in SPOKE_REGIONS:
                try:
                    INSTANCE_LIST = []
                    EC2_CLIENT = get_boto3_client(
                        STS_CLIENT, account_id, args.role_name, "ec2", spoke_region
                    )
                    EC2_RESOURCE = get_boto3_resource(
                        STS_CLIENT, account_id, args.role_name, "ec2", spoke_region
                    )
                    INSTANCE_AMI_INFO = get_instance_and_ami_ids(EC2_CLIENT)
                    REPORT = create_report(
                        INSTANCE_AMI_INFO,
                        ou_name,
                        account_id,
                        account_name,
                        spoke_region,
                        EC2_RESOURCE,
                    )
                    print_to_console(REPORT)
                    add_info_to_csv_file(REPORT, args.output_file)
                except Exception as exception:
                    error_code = str(exception.response.get("Error").get("Code"))
                    if error_code == "ExpiredToken":
                        raise exception
                    REPORT_ROW = [
                        dict(
                            ou_name=ou_name,
                            account_id=account_id,
                            account_name=account_name,
                            spoke_region=spoke_region,
                            instance_id=error_code,
                            image_id="*",
                            image_platform="*",
                            platform_details="*",
                            public="*",
                            owner_id="*",
                            image_owner_alias="*",
                            description="*",
                            image_type="*",
                        )
                    ]
                    print_to_console(REPORT_ROW)
                    add_info_to_csv_file(REPORT_ROW, args.output_file)
        REMAINING_ACCOUNTS.pop(account_id, None)
        if REMAINING_ACCOUNTS:
            write_temp_file(REMAINING_ACCOUNTS, TEMP_FILE)
        else:
            remove_temp_file(TEMP_FILE)
