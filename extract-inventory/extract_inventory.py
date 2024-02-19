import os
import boto3
import logging
import datetime
import botocore

from pandas import DataFrame, read_csv
from typing import Final
import extraction_utils
import csv
from botocore.exceptions import ClientError


EXTRACT_LAMBDAS: Final = 1
EXTRACT_ROLES: Final = 2
EXTRACT_VPCS: Final = 3
EXTRACT_KMS: Final = 4
EXTRACT_FW: Final = 5
EXTRACT_LG: Final = 6
EXTRACT_SNS: Final = 7
EXTRACT_PORTFOLIOS: Final = 8
EXTRACT_CF: Final = 9
EXTRACT_PRODUCTS: Final = 10
EXTRACT_INSTANCES: Final = 11
EXTRACT_IMAGES: Final = 12
EXTRACT_TAGS: Final = 13
EXTRACT_SES_IDENTITIES: Final = 14
EXTRACT_EVENT_RULES: Final = 15
EXTRACT_SSM_DOCS: Final = 16

EXTRACTION_TYPE: Final = EXTRACT_LG

MAX_ITEM: Final = os.getenv("PAGE_LIMIT", 50)
ARE_SPOKES_INCLUDED: Final = os.getenv(
    "ARE_SPOKES_INCLUDED", "YES"
)  # YES: INCLUDE SPOKES
PROCESS_FAILED_SPOKES: Final = os.getenv(
    "PROCESS_FAILED_SPOKES", "NO"
)  # YES: process failed spokes
IS_ENTERPRISE: Final = os.getenv(
    "IS_ENTERPRISE", "YES"
)  # YES: process enterprise accounts
HUB_NAMES: Final = os.getenv("HUB_NAMES", "WE1-P2")
EXTRACT_LOGS = os.getenv("EXTRACT_LOGS", "NO")
ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  # ALL, Prod, NonProd, Sandbox
ACCOUNT_TYPE = os.getenv(
    "ACCOUNT_TYPE", "ALL"
)  # ALL, Foundation, Standalone, Sandbox, Connected, Specific
SEARCH_REGION = os.getenv(
    "SEARCH_REGION",
    "eu-west-1",
)  # SEARCH_REGION = os.getenv("SEARCH_REGION", "eu-west-1")
KEY_TAG_NAME = "cip-"
SPECIFIC_ACCOUNT = "768961172930"
EXTRACT_TAGS_RESOURCE_TYPE = os.getenv("EXTRACT_TAGS_RESOURCE_TYPE", "EC2")
RESUME_EXTRACTION = os.getenv("RESUME_EXTRACTION", "NO")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"max item: {MAX_ITEM}")


def get_ddb_table(session: boto3.session.Session):
    client_ddb = session.client("dynamodb")

    response_dynamodb = client_ddb.list_tables()
    _table_name = None
    if "TableNames" in response_dynamodb and len(response_dynamodb["TableNames"]) > 0:
        _table_name = response_dynamodb["TableNames"][0]

    return _table_name


def get_account_ids(_table_name: str, account_type="ALL", region: str = "eu-west-1"):
    if account_type == "Specific":
        return {SPECIFIC_ACCOUNT: SEARCH_REGION}

    if _table_name:
        ddb_resource = dev_session.resource("dynamodb", region_name=region).Table(
            table_name
        )
    else:
        logger.error("table name is not provided")
        return None

    response = ddb_resource.scan(
        FilterExpression="#Status = :status",
        ExpressionAttributeValues={
            ":status": "Active",
        },
        ExpressionAttributeNames={"#Status": "status"},
    )
    data = response["Items"]

    while "LastEvaluatedKey" in response:
        response = ddb_resource.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.extend(response["Items"])
    _account_ids = {
        account["account"]: account["region"] if "region" in account else "eu-west-1"
        for account in data
        if "account" in account and account["status"] == "Active"
    }

    if ENVIRONMENT_TYPE != "ALL":
        _account_ids = {
            account["account"]: account["region"]
            for account in data
            if "environment-type" in account
            and account["environment-type"] == ENVIRONMENT_TYPE
        }
    if account_type != "ALL":
        _account_ids = {
            account["account"]: account["region"]
            for account in data
            if "account-type" in account and account["account-type"] == account_type
        }

    return _account_ids


def tag_date():
    today = datetime.datetime.today()
    YEAR = today.year
    MONTH = today.month
    DAY = today.day
    tim = f"{today.time()}"
    TIME_STR = f"{tim[:8].replace(':', '_')}"
    file_name_head = f"{YEAR}_{MONTH:02d}_{DAY:02d}_{TIME_STR}"
    return file_name_head


def key_word_to_sort(extraction_type: int):
    if extraction_type == EXTRACT_LAMBDAS:
        return "runtime"
    elif extraction_type == EXTRACT_ROLES:
        return "rolename"
    elif extraction_type == EXTRACT_VPCS:
        return "account_id"
    elif extraction_type == EXTRACT_KMS:
        return "aliases"
    elif extraction_type == EXTRACT_FW:
        return "firewall_name"
    elif extraction_type == EXTRACT_LG:
        return "log_group_name"
    elif extraction_type == EXTRACT_SNS:
        return "topic_arn"
    elif extraction_type == EXTRACT_PORTFOLIOS:
        return "PortfolioName"
    elif extraction_type == EXTRACT_CF:
        return "stack_name"
    elif extraction_type == EXTRACT_PRODUCTS:
        return "account_id"
    elif extraction_type == EXTRACT_INSTANCES:
        return "account_id"
    elif extraction_type == EXTRACT_IMAGES:
        return "image_id"
    elif extraction_type == EXTRACT_TAGS:
        return "account_id"
    elif extraction_type == EXTRACT_SES_IDENTITIES:
        return "account_id"
    elif extraction_type == EXTRACT_EVENT_RULES:
        return "account_id"
    elif extraction_type == EXTRACT_SSM_DOCS:
        return "account_id"
    else:
        raise Exception("incorrect extraction type")


def extraction(
    session: boto3.session.Session,
    _account_id: str = None,
    what_to_extract: int = EXTRACT_LAMBDAS,
    _region: str = "eu-west-1",
):
    if what_to_extract == EXTRACT_LAMBDAS:
        return extraction_utils.extract_functions(
            session, _account_id, _region, EXTRACT_LOGS, MAX_ITEM
        )
    elif what_to_extract == EXTRACT_ROLES:
        return extraction_utils.extract_roles(session, _account_id, _region, MAX_ITEM)
    elif what_to_extract == EXTRACT_VPCS:
        return extraction_utils.extract_vpcs(
            session, _account_id, _region, KEY_TAG_NAME, MAX_ITEM
        )
    elif what_to_extract == EXTRACT_KMS:
        return extraction_utils.extract_kms(session, _account_id, _region, MAX_ITEM)
    elif what_to_extract == EXTRACT_LG:
        return extraction_utils.extract_log_groups(
            session, _account_id, _region, MAX_ITEM
        )
    elif what_to_extract == EXTRACT_SNS:
        return extraction_utils.extract_sns(session, _account_id, _region)
    elif what_to_extract == EXTRACT_PORTFOLIOS:
        return extraction_utils.extract_portfolios(session, _account_id, _region)
    elif what_to_extract == EXTRACT_CF:
        return extraction_utils.extract_cloud_formations(session, _account_id, _region)
    elif what_to_extract == EXTRACT_PRODUCTS:
        return extraction_utils.extract_provisioned_products(
            session, _account_id, _region
        )
    elif what_to_extract == EXTRACT_INSTANCES:
        return extraction_utils.extract_instances(session, _account_id, _region)
    elif what_to_extract == EXTRACT_IMAGES:
        return extraction_utils.extract_images(session, _account_id, SEARCH_REGION)
    elif what_to_extract == EXTRACT_TAGS:
        return extraction_utils.extract_tags(
            session,
            _account_id,
            _region,
            KEY_TAG_NAME,
            MAX_ITEM,
            EXTRACT_TAGS_RESOURCE_TYPE,
        )
    elif what_to_extract == EXTRACT_SES_IDENTITIES:
        return extraction_utils.extract_ses_verified_identities(
            session, _account_id, _region
        )
    elif what_to_extract == EXTRACT_EVENT_RULES:
        return extraction_utils.extract_event_rules(session, _account_id, _region)
    elif what_to_extract == EXTRACT_SSM_DOCS:
        return extraction_utils.extract_ssm_documents(session, _account_id, _region)
    else:
        raise Exception("no proper option was given")


hub_names = HUB_NAMES.split(",")
regions = SEARCH_REGION.split(",")

for hub_name in hub_names:
    for one_region in regions:
        error_reports = []
        function_reports = []

        if IS_ENTERPRISE.lower() == "yes":
            enterprise_profile = f"{hub_name}-role_DEVOPS"
            dev_session = boto3.session.Session(
                profile_name=enterprise_profile, region_name=one_region
            )
        else:
            PROFILE = f"{hub_name}-role_READONLY"
            try:
                dev_session = boto3.session.Session(
                    profile_name=PROFILE, region_name=one_region
                )
            except botocore.exceptions.ProfileNotFound:
                PROFILE = f"{hub_name}-role_DEVOPS"
                dev_session = boto3.session.Session(
                    profile_name=PROFILE, region_name=one_region
                )

        if ARE_SPOKES_INCLUDED.lower() == "yes":
            logger.info(f"profile name: {PROFILE}")

            if RESUME_EXTRACTION.lower() == "yes":
                try:
                    with open("resume-extraction.csv") as f:
                        reader = csv.reader(f)
                        next(reader)  # skips header
                        account_ids = {row[0]: row[1] for row in reader}
                except FileNotFoundError:
                    logger.error(
                        "resume-extraction.csv file not found, please run the script without RESUME_EXTRACTION=NO"
                    )
                    break
            # iterate through the list of failed account ids
            elif PROCESS_FAILED_SPOKES.lower() == "yes":
                df_failures = read_csv(f"errors_{hub_name}_{one_region}.csv")
                account_ids = df_failures["0"].to_list()
            else:
                table_name = get_ddb_table(dev_session)
                if table_name is None:
                    logger.warning(
                        f"there is no table for the region {one_region} in the hub {hub_name}"
                    )
                    continue
                account_ids = get_account_ids(table_name, ACCOUNT_TYPE, one_region)

                if account_ids is None:
                    logger.warning(
                        f"there are no accounts for the region {one_region} in the hub {hub_name}"
                    )
                    continue

            accounts = account_ids.items()
            total_accounts = len(accounts)
            i = 1
            index = 0
            for account_id, _region in accounts:
                logger.info(f"account_id:{account_id} is in progress")
                logger.info(f"account {i} of {total_accounts}")
                i += 1
                try:
                    tmp_list = extraction(
                        dev_session, account_id, EXTRACTION_TYPE, _region
                    )
                    if tmp_list is None:
                        error_reports.append((account_id, "assume error"))
                    else:
                        function_reports.extend(tmp_list)
                    index += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ExpiredToken":
                        logger.warning(f"An exception occurred:{e}")
                        logger.warning(
                            "To resume the extraction, refresh the token and run the script again with RESUME_EXTRACTION=YES"
                        )
                        with open("resume-extraction.csv", "w", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(["account_id", "region"])
                            accounts = list(accounts)[index:]
                            for acccount in accounts:
                                writer.writerow(acccount)
                        logger.info(
                            "the unprocessed accounts can be found in resume-extraction.csv"
                        )
                        break
                except Exception as e:
                    logger.error(f"An exception occurred:{e}")
                    error_reports.append((account_id, e))

        elif ARE_SPOKES_INCLUDED.lower() == "no":
            try:
                tmp_list = extraction(dev_session, None, EXTRACTION_TYPE)
                if tmp_list is None:
                    error_reports.append((hub_name, "assume error"))
                else:
                    function_reports.extend(tmp_list)

            except Exception as e:
                logger.error(f"An exception occurred:{e}")
                error_reports.append((hub_name, e))

        if len(function_reports) > 0:
            function_reports = sorted(
                function_reports,
                key=lambda x: x[key_word_to_sort(EXTRACTION_TYPE)],
                reverse=False,
            )
            df = DataFrame(function_reports)
            df.to_csv(
                f"{key_word_to_sort(EXTRACTION_TYPE)}_{hub_name}_{'' if ARE_SPOKES_INCLUDED.lower() == 'no' else 'spokes'}_{one_region}_{ACCOUNT_TYPE}_{ENVIRONMENT_TYPE}_{tag_date()}.csv",
                index=False,
            )
        else:
            logger.warning(
                f"no data found for the extraction {EXTRACTION_TYPE} for the account id {account_id if IS_ENTERPRISE == 'NO' else hub_name } in {one_region}"
            )

        if len(error_reports) > 0:
            df_errors = DataFrame(error_reports)
            df_errors.to_csv(f"errors_{hub_name}_{SEARCH_REGION}.csv", index=False)

        logger.info(
            f"extraction type is {EXTRACTION_TYPE} for {hub_name} completed.. in the region {one_region}"
        )
