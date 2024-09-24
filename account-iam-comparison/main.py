#!/usr/bin/env python3.9

# fetch iam roles and filter based on a role name prefix
# fetch all iam policies attached to the roles
# fetch the policy document for each policy
# fetch the policy document for each policy version

import boto3
import deepdiff
import json
from dataclasses import dataclass
from typing import List


@dataclass(order=True)
class Policy:
    name: str
    document: dict


@dataclass(order=True)
class Role:
    name: str
    policies: List[Policy]


@dataclass(order=True)
class Account:
    name: str
    ce: str
    roles: List[Role]


# set the region to use
region = "us-east-1"


def fetch_iam(client, role_name_prefix, role_suffixes=None) -> List[Role]:
    # fetch all IAM roles
    if role_suffixes is None:
        role_suffixes = []
    paginator = client.get_paginator("list_roles")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": 100})
    roles = []
    for page in page_iterator:
        roles.extend(
            Role(role["RoleName"], get_iam_role_policies(client, role["RoleName"]))
            for role in page["Roles"]
            if role["RoleName"].startswith(role_name_prefix)
            and any(role["RoleName"].endswith(s) for s in role_suffixes)
        )

    return sorted(roles, key=lambda x: x.name)


def get_iam_role_policies(client, role_name) -> List[Policy]:
    """Returns a list of IAM policies attached to the role."""
    paginator = client.get_paginator("list_attached_role_policies")
    page_iterator = paginator.paginate(
        RoleName=role_name, PaginationConfig={"PageSize": 100}
    )
    policies = []
    for page in page_iterator:
        policies.extend(
            Policy(
                policy["PolicyName"],
                get_iam_policy_document(client, policy["PolicyArn"]),
            )
            for policy in page["AttachedPolicies"]
        )

    return sorted(policies, key=lambda x: x.name)


def get_iam_policy_document(client, policy_arn) -> dict:
    """Returns the policy document for the IAM policy."""
    # fetch the policy document for the policy
    # list the policy versions and get the latest version
    # return the policy document for the latest version
    paginator = client.get_paginator("list_policy_versions")
    page_iterator = paginator.paginate(
        PolicyArn=policy_arn, PaginationConfig={"PageSize": 100}
    )
    versions = []
    for page in page_iterator:
        versions.extend(page["Versions"])
    latest_version = max(versions, key=lambda v: v["VersionId"])
    policy_version = client.get_policy_version(
        PolicyArn=policy_arn, VersionId=latest_version["VersionId"]
    )
    return policy_version["PolicyVersion"]["Document"]


if __name__ == "__main__":
    beta_account = Account("WE1-B1", "WE1-B1-0105", [])
    preprod_account = Account("WE1-T1", "WE1-T1-0010", [])
    access_roles = [
        "-role_OPERATIONS",
        "-role_NETWORK-ADM",
        "-role_NETWORK-RO",
        "-role_IAM-ADM",
        "-role_DS-RO",
        "-role_DS-METADATA",
        "-role_DS-INVESTIGATION",
        "-role_SOC",
        "-role_KMS",
        "-role_COSTOPT",
        "-role_SSM",
        "-role_CLOUDFORMATION",
        "-role_DsServices",
        "-role_DsServicesLambdaExecutionRole",
        "-role_AUTOMATION",
        "-role_UnitScheduler",
        "-role_UnitScheduler_BYOLambda",
        "-role_UnitScheduler_Execution",
        "CIP_SelfService",
        "-role_BACKUP",
    ]

    # create an IAM client
    beta_session = boto3.Session(profile_name=f"{beta_account.name}-role_DEVOPS")
    beta_client = beta_session.client("iam", region_name=region)
    preprod_session = boto3.Session(profile_name=f"{preprod_account.name}-role_DEVOPS")
    preprod_client = preprod_session.client("iam", region_name=region)

    # fetch ce roles
    beta_account.roles = fetch_iam(beta_client, beta_account.ce)
    preprod_account.roles = fetch_iam(preprod_client, preprod_account.ce)

    # fetch access roles
    # beta_account.roles = fetch_iam(beta_client, f"{beta_account.name}-role", access_roles)
    # preprod_account.roles = fetch_iam(preprod_client, f"{preprod_account.name}-role", access_roles)

    diff = deepdiff.DeepDiff(beta_account.roles, preprod_account.roles)
    print(json.dumps(diff, indent=4, sort_keys=True))
