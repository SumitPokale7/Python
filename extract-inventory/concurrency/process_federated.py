import os
import boto3
import logging
import datetime
import botocore
import itertools
import extraction_utils

from csv import reader as csv_reader
from hs_service.aws.dynamodb import DynamoDB
from boto3.dynamodb.conditions import Attr
from math import ceil as math_ceil
from pandas import DataFrame
from typing import Final
from functools import wraps
from time import time
from concurrent.futures import ThreadPoolExecutor

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
EXTRACT_VIRTUAL_GW: Final = 17
EXTRACT_MESH: Final = 18
EXTRACT_AM: Final = 19
EXTRACT_USER_PROFILE: Final = 20
EXTRACT_AMI_BLOCK_PUBLIC_ACCESS: Final = 21
EXTRACTION_TYPE: Final = EXTRACT_AMI_BLOCK_PUBLIC_ACCESS

SERVICE_MAP = {
    EXTRACT_LAMBDAS: "lambda",
    EXTRACT_ROLES: "iam",
    EXTRACT_VPCS: "ec2",
    EXTRACT_FW: "network-firewall",
    EXTRACT_LG: "logs",
    EXTRACT_SNS: "sns",
    EXTRACT_PORTFOLIOS: "servicecatalog",
    EXTRACT_CF: "cloudformation",
    EXTRACT_PRODUCTS: "servicecatalog",
    EXTRACT_INSTANCES: "ec2",
    EXTRACT_IMAGES: "ec2",
    EXTRACT_TAGS: "ec2",
    EXTRACT_SES_IDENTITIES: "ses",
    EXTRACT_EVENT_RULES: "events",
    EXTRACT_SSM_DOCS: "ssm",
    EXTRACT_VIRTUAL_GW: "directconnect",
    EXTRACT_MESH: "appmesh",
    EXTRACT_AM: "ce",
    EXTRACT_USER_PROFILE: "iam",
    EXTRACT_AMI_BLOCK_PUBLIC_ACCESS: "ec2",
}

SUBMIT_LIMIT_PER_PREP = 200
SUBMIT_LIMIT_PER_FETCH = 200

MAX_ITEM: Final = os.getenv("PAGE_LIMIT", 50)
ARE_SPOKES_INCLUDED: Final = os.getenv(
    "ARE_SPOKES_INCLUDED", "YES"
)  # YES: INCLUDE SPOKES
PROCESS_FAILED_SPOKES: Final = os.getenv(
    "PROCESS_FAILED_SPOKES", "NO"
)  # YES: process failed spokes
IS_ENTERPRISE: Final = os.getenv(
    "IS_ENTERPRISE", "NO"
)  # YES: process enterprise accounts

HUB_NAMES: Final = os.getenv("HUB_NAMES", "WH-00H2")

EXTRACT_LOGS = os.getenv("EXTRACT_LOGS", "YES")
ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  # ALL, Prod, NonProd, Sandbox
ACCOUNT_TYPE = os.getenv(
    "ACCOUNT_TYPE", "Connected"
)  # ALL, Foundation, Standalone, Sandbox, Connected, Specific
SEARCH_REGION = os.getenv("SEARCH_REGION", "eu-west-1")
# SEARCH_REGION = os.getenv(
#     "SEARCH_REGION",
#     "eu-west-1")
KEY_TAG_NAME = "cip-"
SPECIFIC_ACCOUNT = "495416159460"
EXTRACT_TAGS_RESOURCE_TYPE = os.getenv("EXTRACT_TAGS_RESOURCE_TYPE", "EC2")
RESUME_EXTRACTION = os.getenv("RESUME_EXTRACTION", "NO")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"max item: {MAX_ITEM}")

REGIONS = SEARCH_REGION.split(",")

error_reports = []
function_reports = []

PROFILE = f"{HUB_NAMES}-role_READONLY"
try:
    dev_session = boto3.session.Session(profile_name=PROFILE, region_name="eu-west-1")
except botocore.exceptions.ProfileNotFound:
    PROFILE = f"{HUB_NAMES}-role_DEVOPS"
    dev_session = boto3.session.Session(profile_name=PROFILE, region_name="eu-west-1")

logger.info(f"profile name: {PROFILE}")


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print("func:%r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap


def get_ddb_table(session: boto3.session.Session):
    client_ddb = session.client("dynamodb")

    response_dynamodb = client_ddb.list_tables()
    _table_name = None
    if "TableNames" in response_dynamodb and len(response_dynamodb["TableNames"]) > 0:
        _table_name = response_dynamodb["TableNames"][0]

    return _table_name


def read_accounts_from_file(filename, resumed_id="-1"):
    with open(filename) as f:
        reader = csv_reader(f)
        next(reader)  # skips header
        _account_dict = {row[0]: row[1] for row in reader if row[0] >= resumed_id}

    return _account_dict


def get_spokes(_filter_expression=None):
    Table_Name = f"{os.getenv('DDB_PREFIX', None)}-DYN_METADATA"
    ddb = DynamoDB(Table_Name)
    if not _filter_expression:
        _filter_expression = Attr("status").eq("Active") & Attr("account-type").ne(
            "Hub"
        )
    spoke_accounts = ddb.get_all_entries(filter_expression=_filter_expression)
    spoke_accounts = sorted(spoke_accounts, key=lambda x: x["account"], reverse=False)

    return spoke_accounts


def get_account_ids():
    try:
        # delete the accounts.csv file between environments
        # or to build the account list from the scratch
        accounts_dict = read_accounts_from_file(f"accounts_{HUB_NAMES}.csv")

    except FileNotFoundError:
        spokes = get_spokes()
        accounts_dict = {
            spoke[
                "account"
            ]: f"{spoke['region'] if 'region' in spoke else 'eu-west-1'}#{spoke['account-type'] if 'account-type' in spoke else 'na'}"
            for spoke in spokes
        }
        DataFrame(list(accounts_dict.items()), columns=["account_id", "region"]).to_csv(
            f"accounts_{HUB_NAMES}.csv", index=False
        )

    return accounts_dict


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
        return "account_id"
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
    elif extraction_type == EXTRACT_SSM_DOCS:
        return "account_id"
    elif extraction_type == EXTRACT_VIRTUAL_GW:
        return "account_id"
    elif extraction_type == EXTRACT_MESH:
        return "account_id"
    elif extraction_type == EXTRACT_AM:
        return "account_id"
    elif extraction_type == EXTRACT_USER_PROFILE:
        return "account_id"
    elif extraction_type == EXTRACT_EVENT_RULES:
        return "account_id"
    elif extraction_type == EXTRACT_AMI_BLOCK_PUBLIC_ACCESS:
        return "account_id"
    else:
        raise Exception("incorrect extraction type")


def create_client(
    service: str, account_id: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        sts_client = hub_session.client("sts")
        role = f"arn:aws:iam::{account_id}:role/CIP_INSPECTOR"
        creds = sts_client.assume_role(
            RoleArn=role, RoleSessionName="LambdaInventorySession"
        )

        client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as err:
        logger.error(err, exc_info=True)
        logger.critical(f"Client error occurred:{err} for role {role}")
        return None

    return client


def extraction(all_args):
    _account_id, _region, session_client, what_to_extract = all_args
    if what_to_extract == EXTRACT_SES_IDENTITIES:
        return extraction_utils.extract_ses_verified_identities(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_LG:
        return extraction_utils.extract_log_groups(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_ROLES:
        return extraction_utils.extract_roles((_account_id, _region, session_client))
    elif what_to_extract == EXTRACT_SSM_DOCS:
        return extraction_utils.extract_ssm_documents(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_VIRTUAL_GW:
        return extraction_utils.extract_virtual_gateways(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_MESH:
        return extraction_utils.extract_meshes((_account_id, _region, session_client))
    elif what_to_extract == EXTRACT_AM:
        return extraction_utils.extract_anomalies_monitor(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_USER_PROFILE:
        return extraction_utils.extract_login_profiles(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_EVENT_RULES:
        return extraction_utils.extract_event_rules(
            (_account_id, _region, session_client)
        )
    elif what_to_extract == EXTRACT_AMI_BLOCK_PUBLIC_ACCESS:
        return extraction_utils.extract_ami_ebs_block_public_access(
            (_account_id, _region, session_client)
        )
    else:
        raise Exception("no proper option was given")


@timing
def build_accounts(_dev_session, client_type, extraction_type):
    _accounts = [
        (a, b.split("#")[0], client_type, extraction_type)
        for a, b in get_account_ids().items()
    ]

    return _accounts


def initialize_clients(initial_param):
    account_id, region, client_type, extraction_type = initial_param
    print(f"Initialize_Client = account_id: {account_id}, region: {region}, client_type: {client_type}")
    region_pop = False
    # make sure no stone is left untouched

    if region not in REGIONS and client_type != "iam":
        logger.info(f"the region {region} added for the account id {account_id}")
        REGIONS.append(region)
        region_pop = True

    temp = [
        (
            account_id,
            one_region,
            create_client(
                client_type,
                account_id,
                one_region,
                dev_session,
            ),
            extraction_type,
        )
        for one_region in REGIONS
    ]

    if region_pop:
        logger.info(f"the region {region} removed for the account id {account_id}")
        REGIONS.pop()
    return temp


if __name__ == "__main__":
    ts = time()
    accounts = build_accounts(
        dev_session, SERVICE_MAP[EXTRACTION_TYPE], EXTRACTION_TYPE
    )
    total_accounts = len(accounts)
    num_of_pages = math_ceil(total_accounts / float(SUBMIT_LIMIT_PER_PREP))
    logger.info(
        f"the total number of accounts to be initialized for all regions: {total_accounts}"
    )

    with ThreadPoolExecutor() as prep_executor:
        preps = []
        for one in range(1, num_of_pages + 1):
            offset = (one - 1) * SUBMIT_LIMIT_PER_PREP
            logger.info(f"the %{(one / num_of_pages)*100} percent prepared")
            for result in prep_executor.map(
                initialize_clients, accounts[offset: offset + SUBMIT_LIMIT_PER_PREP]
            ):
                if result and len(result) > 0:
                    preps.extend(result)

    tp = time()
    logger.info(f"preparation is completed in {tp - ts} seconds")

    with ThreadPoolExecutor() as result_executor:
        results = []
        total_accounts = len(preps)
        num_of_pages = math_ceil(total_accounts / float(SUBMIT_LIMIT_PER_FETCH))

        for one in range(1, num_of_pages + 1):
            offset = (one - 1) * SUBMIT_LIMIT_PER_FETCH
            logger.info(f"the %{(one / num_of_pages) * 100} percent completed")
            try:
                results.extend(
                    list(
                        itertools.chain.from_iterable(
                            [
                                result
                                for result in result_executor.map(
                                    extraction,
                                    preps[offset: offset + SUBMIT_LIMIT_PER_FETCH],
                                )
                                if result and len(result) > 0
                            ]
                        )
                    )
                )
            except Exception as ex:
                function_reports = sorted(
                    results,
                    key=lambda x: x[key_word_to_sort(EXTRACTION_TYPE)],
                    reverse=False,
                )
                df = DataFrame(function_reports)
                df.to_csv(
                    f"{key_word_to_sort(EXTRACTION_TYPE)}_{HUB_NAMES}_ALL_{ACCOUNT_TYPE}_{ENVIRONMENT_TYPE}_{tag_date()}.csv",
                    index=False,
                )
                raise ex

    tr = time()
    logger.info(f"fetching results is completed in {tr - ts} seconds")

    function_reports = sorted(
        results,
        key=lambda x: x[key_word_to_sort(EXTRACTION_TYPE)],
        reverse=False,
    )
    _accounts_dict = read_accounts_from_file(f"accounts_{HUB_NAMES}.csv")

    append_account_type = [
        dict(
            customer,
            **{"account-type": _accounts_dict[customer["account_id"]].split("#")[1]},
        )
        for customer in function_reports
    ]
    df = DataFrame(append_account_type)
    df.to_csv(
        f"{key_word_to_sort(EXTRACTION_TYPE)}_{HUB_NAMES}_ALL_{ACCOUNT_TYPE}_{ENVIRONMENT_TYPE}_{tag_date()}.csv",
        index=False,
    )
    te = time()
    logger.info(
        f"extraction type is {EXTRACTION_TYPE} for {HUB_NAMES} completed in {te-ts} seconds"
    )
