#!/usr/bin/env python3
import logging
import os
import sys
from functools import lru_cache
from typing import Tuple

import boto3
import botocore.exceptions
from cloudenvironments.cloud_environments import CloudEnvironment

logging.basicConfig(
    force=True, level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

_log = logging.getLogger("cli")

DRY_RUN = False
AWS_PROFILE_SUFFIX = "-role_DEVOPS"
AWS_REGIONS = dict(
    WE1="eu-west-1",
    WU2="us-east-2",
)


def usage():
    print(f"Usage: ./{os.path.basename(__file__)} <account>[, <account>]")
    print()
    print("Parameters:")
    print("    -h, --help       - display help")
    print("    -n, --dry-run    - execute without real action")
    print()


def get_region(alias: str) -> str:
    code = alias.split("-", 1)[0]
    assert code in AWS_REGIONS, f"[{alias}] could not detect region"
    return AWS_REGIONS[code]


def get_profile(alias: str) -> str:
    return f"{alias}{AWS_PROFILE_SUFFIX}"


@lru_cache
def session_factory(alias: str) -> boto3.Session:
    profile = get_profile(alias)
    region = get_region(alias)

    _log.debug(f"[{alias}] init session for {profile!r} ({region!r}) ...")

    return boto3.Session(profile_name=profile, region_name=region)


@lru_cache
def cloud_env_factory(alias: str) -> CloudEnvironment:
    _log.debug(f"[{alias}] init cloud environment ...")

    session = session_factory(alias)
    credentials = session.get_credentials()

    return CloudEnvironment(
        credentials=dict(
            AccessKeyId=credentials.access_key,
            SecretAccessKey=credentials.secret_key,
            SessionToken=credentials.token,
        ),
        region=session.region_name,
    )


def resolve_accounts(alias: str) -> Tuple[str, str, str, str, bool]:
    _log.info(f"[{alias}] resolving account ...")

    access = True
    account_id = ""
    region = ""
    profile = get_profile(alias)

    try:
        session = session_factory(alias)

        region = session.region_name or ""

        account_id = session.client("sts").get_caller_identity()["Account"]
    except (botocore.exceptions.ClientError, botocore.exceptions.ProfileNotFound):
        access = False

    return (alias, region, account_id, profile, access)


def sync_tags(alias: str) -> None:
    _log.info(f"[{alias}] syncing tags ...")

    cloud_env = cloud_env_factory(alias)

    _log.debug(f"[{alias}] loading CE names for {alias!r} ...")

    ce_names = cloud_env.list_ces()

    total = len(ce_names)

    _log.info(f"[{alias}] loaded {total} CE names ...")

    ces = []

    for idx, name in enumerate(ce_names, start=1):
        _log.info(f"[{alias}] handling CE {name!r} ({idx} of {total}) ...")
        ces.append(
            (
                name,
                cloud_env.sync_ce_tags(name),
            )
        )

    synced_ces = [ce for ce in ces if ce[1]]

    _log.info(
        f"[{alias}] synced {len(synced_ces)}/{len(ces)}: {','.join(x[0] for x in synced_ces) or '-'}"
    )


def main():
    if any([v.lower() in ["-h", "--help"] for v in sys.argv]):
        usage()
        exit(0)

    global DRY_RUN
    DRY_RUN = any([v.lower() in ["-n", "--dry-run"] for v in sys.argv])

    account_names = sorted(set(sys.argv[1:]))

    if not account_names:
        print("Error: provide at least one account name.")
        usage()
        sys.exit(1)

    print("Starting ...")

    accounts = [resolve_accounts(name) for name in account_names]

    not_auth_roles = [acc[-2] for acc in accounts if not acc[-1]]

    if not_auth_roles:
        print(
            f"Error: found {len(not_auth_roles)} not authorized roles: {','.join(not_auth_roles)}",
            file=sys.stderr,
        )
        print("Refresh credentials:", file=sys.stderr)
        print(
            f"/path/to/awsconnect --role {' --role '.join(not_auth_roles)}",
            file=sys.stderr,
        )
        print("And try again!", file=sys.stderr)
        sys.exit(1)

    print()
    print(f"Found {len(accounts)} accounts:")
    for alias, region, account_id, _, _ in accounts:
        print(f" - {alias} : {account_id} / {region}")

    print()
    input("Proceed? <Ctrl-C> to abort ... ")
    print()

    for account in accounts:
        sync_tags(account[0])

    print("DONE")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Aborted, bye.")
        exit(130)
