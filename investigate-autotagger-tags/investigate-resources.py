# Standard library imports
import os
import logging

# Related third party imports
import boto3

# Local application/library specific imports

logging.basicConfig(level=logging.INFO)

# This is commented out so that someone does not accidently run this against all accounts
# Please uncomment if you want to run against all accounts
# accounts_names = ['A1', 'B1', 'U1', 'T1', 'P1', 'P2', 'P3', 'O2', 'O3']
accounts_names = ["A1"]

regions = {"WU2": "us-east-2", "AccountName": "eu-west-1"}

tagged_resource_types = [
    "network-interface",
    "instance",
    "loadbalancer",
    "targetgroup",
    "security-group",
    "volume",
    "snapshot",
    "image",
    "stack",
]

all_accounts_summary = {}


def process_accounts():
    for account_name in accounts_names:
        for region_alias, region in regions.items():
            process_account(account_name, region_alias)


def process_account(account_name, region_alias):
    resource_arns = []
    resource_prefixes = []

    os.environ["AWS_DEFAULT_REGION"] = regions[region_alias]
    os.environ["AWS_DEFAULT_PROFILE"] = f"{region_alias}-{account_name}-role_DEVOPS"

    logging.info(
        f"Processing {account_name} [{accounts_names.index(account_name)}|{len(accounts_names)}] in {regions[region_alias]}..."
    )

    boto3.setup_default_session(
        region_name=os.environ["AWS_DEFAULT_REGION"],
        profile_name=os.environ["AWS_DEFAULT_PROFILE"],
    )

    api_client = boto3.client("resourcegroupstaggingapi")

    try:
        paginator = api_client.get_paginator("get_resources")
        response = paginator.paginate(
            TagFilters=[
                {"Key": "cloud-environment", "Values": []},
            ],
        ).build_full_result()

        if "ResourceTagMappingList" not in response:
            logging.error(response)
            raise Exception("Invalid response data.")

        resource_list = response["ResourceTagMappingList"]

        for resource in resource_list:
            resource_arn = resource["ResourceARN"]
            resource_type = resource_arn.split(":")[5].split("/")[0]
            if (
                resource_arn[:13] != "arn:aws:s3:::"
                and resource_type not in tagged_resource_types
            ):
                resource_prefix = _get_resource_prefix(resource_arn)
                resource_arns.append(resource_arn)
                resource_prefixes.append(resource_prefix)

        resource_prefixes_summary = _count_resources(resource_prefixes)

        _write_summary(account_name, region_alias, resource_prefixes_summary)

        _write_full_report(account_name, region_alias, resource_arns)

    except Exception as e:
        raise e


def _get_resource_prefix(resource_arn):
    if "/" in resource_arn:
        resource_prefix = resource_arn.split("/")[0]
    elif resource_arn[0:20] == "arn:aws:codepipeline":
        resource_prefix = ":".join(resource_arn.split(":")[0:5])
    elif resource_arn[0:11] == "arn:aws:sns":
        resource_prefix = ":".join(resource_arn.split(":")[0:5])
    else:
        resource_prefix = ":".join(resource_arn.split(":")[0:6])
    return resource_prefix


def _count_resources(resource_prefixes):
    counted_resources = {}
    for prefix in resource_prefixes:
        if prefix not in counted_resources.keys():
            counted_resources[prefix] = 1
        else:
            counted_resources[prefix] += 1

        if prefix not in all_accounts_summary.keys():
            all_accounts_summary[prefix] = 1
        else:
            all_accounts_summary[prefix] += 1
    return counted_resources


def _write_summary(account_name, region_alias, summary):
    sorted_summary = sorted(summary.items(), key=lambda x: x[1], reverse=True)

    with open(f"{region_alias}-{account_name}-summary.csv", "w") as file:
        file.write("Arn,Count\n")
        for key, value in sorted_summary:
            file.write(f"{key},{value}\n")


def _write_full_report(account_name, region_alias, resource_arns):
    with open(f"{region_alias}-{account_name}-report.csv", "w") as file:
        file.write("Arn\n")
        for arn in resource_arns:
            file.write(f"{arn}\n")


if __name__ == "__main__":
    process_accounts()
    _write_summary("accounts", "all", all_accounts_summary)
