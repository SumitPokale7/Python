import os
import boto3
import logging
import datetime

from pandas import DataFrame, read_csv
from typing import Final
import remove_sc_utils

REMOVE_PRODUCTS: Final = 1

REMOVE_TYPE: Final = REMOVE_PRODUCTS

MAX_ITEM: Final = os.getenv("PAGE_LIMIT", 50)
ARE_SPOKES_INCLUDED: Final = os.getenv(
    "ARE_SPOKES_INCLUDED", "NO"
)  # YES: INCLUDE SPOKES
PROCESS_FAILED_SPOKES: Final = os.getenv(
    "PROCESS_FAILED_SPOKES", "NO"
)  # YES: process failed spokes
IS_ENTERPRISE: Final = os.getenv(
    "IS_ENTERPRISE", "YES"
)  # YES: process enterprise accounts
HUB_NAMES: Final = os.getenv("HUB_NAMES", "AccountName-U1,AccountName-T1,WU2-U1,WU2-T1")
EXTRACT_LOGS = os.getenv("EXTRACT_LOGS", "YES")
ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  # ALL, Prod, NonProd, Sandbox
ACCOUNT_TYPE = os.getenv(
    "ACCOUNT_TYPE", "ALL"
)  # ALL, Foundation, Standalone, Sandbox, Connected, Specific
SEARCH_REGION = os.getenv(
    "SEARCH_REGION",
    "eu-west-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,eu-central-1,eu-north-1,eu-west-2,eu-west-3,us-east-1,us-east-2,us-west-2",
)  # ap-southeast-1, eu-west-1, us-east-1, ap-southeast-2, us-east-2, ap-southeast-3
KEY_TAG_NAME = "BP-AWS-ADConnectorID"
SPECIFIC_ACCOUNT = "550590017392"


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

    mylist = list(dict.fromkeys(_account_ids))
    print(len(mylist))

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
    if extraction_type == REMOVE_PRODUCTS:
        return "account_id"
    else:
        raise Exception("incorrect extraction type")


def extraction(
    session: boto3.session.Session,
    _account_id: str = None,
    what_to_extract: int = REMOVE_PRODUCTS,
    _region: str = "eu-west-1",
):
    if what_to_extract == REMOVE_PRODUCTS:
        return remove_sc_utils.extract_provisioned_products(
            session, _account_id, _region
        )
    else:
        raise Exception("no proper option was given")


hub_names = HUB_NAMES.split(",")
regions = SEARCH_REGION.split(",")

for hub_name in hub_names:
    for _region in regions:
        error_reports = []
        function_reports = []

        if IS_ENTERPRISE.lower() == "yes":
            enterprise_profile = f"{hub_name}-role_DEVOPS"
            dev_session = boto3.session.Session(
                profile_name=enterprise_profile, region_name=_region
            )
        else:
            PROFILE = f"{hub_name}-role_DEVOPS"
            dev_session = boto3.session.Session(
                profile_name=PROFILE, region_name=_region
            )

        if ARE_SPOKES_INCLUDED.lower() == "yes":
            logger.info(f"profile name: {PROFILE}")

            # iterate through the list of failed account ids
            if PROCESS_FAILED_SPOKES.lower() == "yes":
                df_failures = read_csv(f"errors_{hub_name}_{_region}.csv")
                account_ids = df_failures["0"].to_list()
            else:
                table_name = get_ddb_table(dev_session)
                account_ids = get_account_ids(table_name, ACCOUNT_TYPE, _region)
            total_accounts = len(account_ids)
            i = 1

            for account_id, _region in account_ids.items():
                logger.info(f"account_id:{account_id} is in progress")
                logger.info(f"account {i} of {total_accounts}")
                i += 1
                try:
                    # tmp_list = extract_functions(dev_session, account_id)
                    tmp_list = extraction(dev_session, account_id, REMOVE_TYPE, _region)
                    if tmp_list is None:
                        error_reports.append((account_id, "assume error"))
                    else:
                        function_reports.extend(tmp_list)

                except Exception as e:
                    logger.error(f"An exception occurred:{e}")
                    error_reports.append((account_id, e))

        elif ARE_SPOKES_INCLUDED.lower() == "no":
            try:
                tmp_list = extraction(dev_session, None, REMOVE_TYPE)
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
                key=lambda x: x[key_word_to_sort(REMOVE_TYPE)],
                reverse=False,
            )
            df = DataFrame(function_reports)
            df.to_csv(
                f"{key_word_to_sort(REMOVE_TYPE)}_{hub_name}_{'' if ARE_SPOKES_INCLUDED.lower() == 'no' else 'spokes'}_{_region}_{ACCOUNT_TYPE}_{ENVIRONMENT_TYPE}_{tag_date()}.csv",
                index=False,
            )
        else:
            logger.warning(
                f"no data found for the extraction {REMOVE_TYPE} for the account id {account_id if IS_ENTERPRISE == 'NO' else hub_name } in {_region}"
            )

        if len(error_reports) > 0:
            df_errors = DataFrame(error_reports)
            df_errors.to_csv(f"errors_{hub_name}_{_region}.csv", index=False)

        logger.info(f"fetching removal type {REMOVE_TYPE} for {hub_name} completed..")
