# -----------------------------------------------------------------
# process_enterprise.py
#
# Extracts resources from enterprise environments based on the cloud environments
# Update TARGET_ENVS to define the environment to be extracted
# Adjust SUBMIT_LIMIT_PER_FETCH to optimize your local machine resources and to avoid throttling
#
# -----------------------------------------------------------------

import boto3
import logging
import datetime
import botocore
import itertools
import extraction_utils

from csv import reader as csv_reader

from math import ceil as math_ceil
from pandas import DataFrame
from typing import Final
from functools import wraps
from time import time
from concurrent.futures import ThreadPoolExecutor

EXTRACT_CE_RESOURCES: Final = 111

EXTRACTION_TYPE: Final = EXTRACT_CE_RESOURCES

SERVICE_MAP = {
    EXTRACT_CE_RESOURCES: "resourcegroupstaggingapi",
}

SUBMIT_LIMIT_PER_FETCH = 50

ALPHA_CE_NAMES: Final = ["WU2-A1", "WE1-A1"]
BETA_CE_NAMES: Final = ["WU2-U1", "WE1-U1", "WU2-B1", "WE1-B1"]
PREPROD_CE_NAMES: Final = ["WE1-T1", "WU2-T1", "WE1-O2", "WE1-P2", "WU2-P2"]
PROD_CE_NAMES: Final = ["WE1-O3", "WU2-P3", "WE1-P3", "WU2-P1", "WE1-P1"]
EVERY_CE_NAMES: Final = (
    ALPHA_CE_NAMES + BETA_CE_NAMES + PREPROD_CE_NAMES + PROD_CE_NAMES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

error_reports = []
function_reports = []

TARGET_ENVS = ALPHA_CE_NAMES


def get_session(ce_name, region):
    PROFILE = f"{ce_name}-role_DEVOPS"
    try:
        dev_session = boto3.session.Session(profile_name=PROFILE, region_name=region)
    except botocore.exceptions.ProfileNotFound:
        PROFILE = f"{ce_name}-role_DEVOPS"
        dev_session = boto3.session.Session(profile_name=PROFILE, region_name=region)

    logger.info(f"profile name: {PROFILE}")
    return dev_session


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print("func:%r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap


def read_accounts_from_file(filename, resumed_id="-1"):
    with open(filename) as f:
        reader = csv_reader(f)
        next(reader)  # skips header
        _accounts = [row[0] for row in reader if row[0] >= resumed_id]

    return _accounts


def get_ce_envs(_env_name, _region: str = "eu-west-1"):
    try:
        dev_session = get_session(_env_name, _region)
        data = read_accounts_from_file(f"{_env_name}_ce_names.csv")

    except FileNotFoundError:
        ddb_resource = dev_session.resource("dynamodb", region_name=_region).Table(
            "CLOUD-ENVIRONMENTS"
        )

        response = ddb_resource.scan(
            AttributesToGet=[
                "cloud-environment",
            ],
            Select="SPECIFIC_ATTRIBUTES",
        )
        data = sorted([item["cloud-environment"] for item in response["Items"]])

        DataFrame(data, columns=["ce_name"]).to_csv(
            f"ce_names_{_env_name}_{_region}.csv", index=False
        )

    return data


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
    if extraction_type == EXTRACT_CE_RESOURCES:
        return "ce_name"
    else:
        raise Exception("incorrect extraction type")


def create_client(
    service: str, role: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        sts_client = hub_session.client("sts")
        creds = sts_client.assume_role(
            RoleArn=role, RoleSessionName="CeInventorySession"
        )

        client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"cannot assume the role: {e}")
        return None

    return client


def extraction(all_args):
    _ce_name, _region, session_client, what_to_extract = all_args
    if what_to_extract == EXTRACT_CE_RESOURCES:
        return extraction_utils.extract_ce_resources(
            (_ce_name, _region, session_client)
        )
    else:
        raise Exception("no proper option was given")


if __name__ == "__main__":
    ts = time()

    ce_names = []
    for env in TARGET_ENVS:
        region = "eu-west-1" if env[0:3] == "WE1" else "us-east-2"

        res_client = get_session(env, region).client("resourcegroupstaggingapi")

        temp = get_ce_envs(env, region)
        ce_names.extend(
            [(item, region, res_client, EXTRACT_CE_RESOURCES) for item in temp]
        )

    with ThreadPoolExecutor() as result_executor:
        results = []
        total_accounts = len(ce_names)
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
                                    ce_names[offset: offset + SUBMIT_LIMIT_PER_FETCH],
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
                    f"{key_word_to_sort(EXTRACTION_TYPE)}_{'_'.join(TARGET_ENVS)}_{tag_date()}.csv",
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
    df = DataFrame(function_reports)
    df.to_csv(
        f"{key_word_to_sort(EXTRACTION_TYPE)}_{'_'.join(TARGET_ENVS)}_{tag_date()}.csv",
        index=False,
    )
    te = time()
    logger.info(
        f"extraction type is {EXTRACTION_TYPE} for {'_'.join(TARGET_ENVS)} completed in {te-ts} seconds"
    )
