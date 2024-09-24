import boto3
import csv
import logging
import argparse
from datetime import datetime
from boto3.dynamodb.conditions import Attr
from hs_service.aws.dynamodb import DynamoDB

parser = argparse.ArgumentParser()
parser.add_argument(
    "--hub-account", type=str, required=True, help="The Hub Account Name"
)
parser.add_argument(
    "--role-to-assume", type=str, required=True, help="The IAM Role to assume"
)
parser.add_argument(
    "--stack-suffix", type=str, required=True, help="The stack suffix to delete"
)
parser.add_argument(
    "--ddb-prefix", type=str, required=True, help="The dynamodb table name prefix"
)
parser.add_argument(
    "--use-global-region",
    help="if provided the the global region will be used" "us-east-1",
    action="store_true",
)

parser.add_argument(
    "--org-units",
    nargs="+",
    help="The organizational units to perform cleanup in e.g. Platform Unmanaged ",
    default=None,
)

parser.add_argument("--no-dry-run", help="Dry run", action="store_false")

args = parser.parse_args()
IAM_ROLE_TO_ASSUME = args.role_to_assume
AE_VERSION_TO_DELETE = f"ae-{args.stack_suffix}-version".lower()
HUB_ACCOUNT = args.hub_account
ORG_CLIENT = boto3.client("organizations")
ORG_UNITS_LIST = args.org_units
DDB_TABLE_NAME = f"{args.ddb_prefix}-DYN_METADATA"


logger = logging.getLogger()

dynamodb = DynamoDB(DDB_TABLE_NAME)


def check_and_remove_attribute(account_name, attribute_to_remove):
    filter_expression = Attr("account-name").eq(account_name)
    response = dynamodb.get_all_entries(filter_expression=filter_expression)
    if response:
        logger.info(f"Record exists with account-name: {account_name}")
        if not args.no_dry_run:
            if attribute_to_remove in response[0]:
                _ = dynamodb.remove_spoke_field(account_name, attribute_to_remove)
                logger.info(
                    f"Removed attribute {attribute_to_remove} from metadata with account-name: {account_name}"
                )
                return "VERSION-EXIST"
            else:
                logger.info(
                    f"Attribute {attribute_to_remove} does not exist in record with account-name: {account_name}"
                )
                return "VERSION-NOT-EXIST"
        else:
            logger.info(
                f"Dry Run enabled. DDB Operation Skipped for account {account_name}"
            )
            return "VERSION-NOT-CHECKED-DRY-RUN"
    else:
        logger.info(f"No record found with account-name: {account_name}")
        return "NO-RECORD-FOUND"


def get_credentials(account_id):
    # Retrieves credentials for a given AWS account ID.
    sts_client = boto3.client("sts")
    spoke_role_arn = f"arn:aws:iam::{account_id}:role/{IAM_ROLE_TO_ASSUME}"
    creds = sts_client.assume_role(
        RoleArn=spoke_role_arn, RoleSessionName="Remove-Template-From-Accounts"
    )
    return creds


def get_assumed_session(creds, spoke_region="us-east-1"):
    # Establishes an assumed session with the provided credentials.
    session = boto3.session.Session(
        region_name=spoke_region,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
    )
    return session


def get_root_id():
    response = ORG_CLIENT.list_roots()
    root_id = response["Roots"][0]["Id"]
    return root_id


def list_organizational_units(parent_id):
    ous = []
    paginator = ORG_CLIENT.get_paginator("list_organizational_units_for_parent")
    for page in paginator.paginate(ParentId=parent_id):
        for ou in page["OrganizationalUnits"]:
            ous.append(ou)
            ous.extend(list_organizational_units(ou["Id"]))
    return ous


def list_organization_units(root_id):
    org_units_with_id = {}
    for org_unit in list_organizational_units(root_id):
        if org_unit.get("Name") in ORG_UNITS_LIST:
            logger.info(
                f"Organization Unit {org_unit.get('Name')} exists. Operation will be performed"
            )
            org_units_with_id[org_unit.get("Id")] = org_unit.get("Name")
    return org_units_with_id


def list_accounts_for_ou_and_sub_ous(ou_id):
    accounts = []
    paginator = ORG_CLIENT.get_paginator("list_accounts_for_parent")
    for page in paginator.paginate(ParentId=ou_id):
        for account in page["Accounts"]:
            accounts.append({"Id": account["Id"], "Name": account["Name"]})

    # Fetch sub OUs and their accounts
    paginator = ORG_CLIENT.get_paginator("list_organizational_units_for_parent")
    for page in paginator.paginate(ParentId=ou_id):
        for ou in page["OrganizationalUnits"]:
            accounts.extend(list_accounts_for_ou_and_sub_ous(ou["Id"]))

    return accounts


def describe_stack(session, stack_name):
    cfn_client = session.client("cloudformation")
    paginator = cfn_client.get_paginator("describe_stacks")
    stack_details = None
    for page in paginator.paginate():
        for stack in page["Stacks"]:
            if stack["StackName"] == stack_name:
                stack_details = stack
                logger.info(
                    f"Found the stack and the name is {stack_name} and details of the stack are {stack_details}"
                )
                return stack_details
    return stack_details


def delete_stack(session, stack_name):
    cfn_client = session.client("cloudformation")
    logger.info(f"Deleting stack {stack_name}")
    cfn_client.delete_stack(StackName=stack_name)
    logger.info(f"Stack {stack_name} deletion initiated.")


def main():
    """
    Main function that orchestrates the fetching of account IDs, retrieval of credentials,
    session assumption, and deleting the automation engine template stack.
    """
    try:
        logger.info(f"Dry Run : {args.no_dry_run}")
        processed_list = []
        root_id = get_root_id()
        org_units = list_organization_units(root_id)

        for org_unit_id, org_unit_name in org_units.items():
            accounts = list_accounts_for_ou_and_sub_ous(org_unit_id)
            logger.info(
                f"Accounts in OU {org_unit_name} are: {accounts} and these will be processed"
            )
            for account_info in accounts:
                try:
                    print(f"account:{account_info.get('Id')} is under processing")
                    spoke_metadata = dynamodb.get_spoke_details_with_account_id(
                        account_info.get("Id")
                    ).get("Items")[0]
                    spoke_region = "us-east-1"
                    if not args.use_global_region:
                        spoke_region = (
                            spoke_metadata.get("region").get("S")
                            if spoke_metadata.get("region")
                            else "eu-west-1"
                        )

                    spoke_name = spoke_metadata.get("account-name").get("S")
                    spoke_id = account_info.get("Id")
                    stack_name = f"{spoke_name}-AE-{args.stack_suffix}"
                    creds = get_credentials(account_info.get("Id"))
                    session = get_assumed_session(creds, spoke_region)
                    logger.info(
                        f"Session established for account {spoke_id} with ID {spoke_name}"
                    )
                    stack_details = describe_stack(session, stack_name)
                    if stack_details is not None:
                        if args.no_dry_run:
                            logger.info(
                                f"Stack {stack_name} exists. Dry run enabled. Stack will not be deleted."
                            )
                            processed_list.append(
                                [f"{org_unit_name};{spoke_id};STACK-EXIST-BUT-DRYRUN"]
                            )
                        else:
                            logger.info(
                                f"Stack {stack_name} exists. Deleting the stack."
                            )
                            delete_stack(session, stack_name)
                            logger.info(
                                f"DDB Operation running for account {account_info.get('Name')}"
                            )
                            result = check_and_remove_attribute(
                                account_info.get("Name"),
                                AE_VERSION_TO_DELETE,
                            )
                            processed_list.append(
                                [f"{org_unit_name};{spoke_id};STACK-PURGED;{result}"]
                            )

                    else:
                        logger.info(
                            f"Stack {stack_name} does not exist. Still checking for account {account_info.get('Name')} "
                            f"metadata in DDB."
                        )
                        result = check_and_remove_attribute(
                            account_info.get("Name"),
                            AE_VERSION_TO_DELETE,
                        )
                        processed_list.append(
                            [f"{org_unit_name};{spoke_id};STACK-NOT-EXIST;{result}"]
                        )
                except Exception as exception_message:
                    if "AccessDenied" in str(exception_message):
                        logger.error(
                            f"Access Denied for Account ID: {account_info.get('Id')}"
                        )
                        processed_list.append(
                            [
                                f"{org_unit_name};{account_info.get('Id')};NA;ACCESS-ERROR"
                            ]
                        )
                    else:
                        processed_list.append(
                            [
                                f"{org_unit_name};{account_info.get('Id')};NA;GENERIC-ERROR"
                            ]
                        )

        # current date and time
        date_time = datetime.now()
        _format = "%Y-%m-%d-%H-%M-%S"

        with open(
            f'{args.ddb_prefix}_{date_time.strftime(_format)}_{"" if not args.no_dry_run else "not_"}processed.csv',
            "w",
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerows(processed_list)

        if not args.no_dry_run:
            logger.info(
                f"the template {args.stack_suffix} would have been purged but dry run is set to True"
            )
        else:
            logger.info(f"the template {args.stack_suffix} is purged successfully")

    except Exception as exception_message:
        if "ExpiredTokenException" in str(exception_message):
            logger.error(
                f"Expired Token Exception: {exception_message}, Generate new token and try again."
            )
        else:
            logger.error(exception_message)


if __name__ == "__main__":
    main()
