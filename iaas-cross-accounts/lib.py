#!/usr/bin/env python3
import concurrent.futures
import functools
import logging
import sys
import re
import time
from functools import lru_cache
from typing import Callable, List, Optional

import boto3
import botocore.exceptions

logging.basicConfig(
    force=True, level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

_log = logging.getLogger("common")

AWS_PROFILE_SUFFIX = "-role_DEVOPS"

AWS_REGIONS = dict(
    AccountName="eu-west-1",
    WU2="us-east-2",
)

FLAGS_HELP = ("-h", "--help")
FLAGS_DRY_RUN = ("-n", "--dry-run")

CE_REGEX = r"(W[EU]\d-[ABUTPO]\d-[A-Z0-9]{4})([^0-9A-Z]?|$)"


class Account:
    def __init__(
        self,
        alias: str,
        region: str,
        profile: str,
        account_id: str,
        session: Optional[boto3.Session],
    ) -> None:
        self.alias = alias.strip()
        self.region = region.strip().lower()
        self.profile = profile.strip()
        self._account_id = account_id.strip()
        self._session = session

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(alias={self.alias!r}, region={self.region!r}, profile={self.profile!r}, resolved={self.resolved!r})"

    @property
    def resolved(self) -> bool:
        return self._account_id is not None and self._session is not None

    @property
    def account_id(self) -> str:
        if not self._account_id:
            raise AccountNotResolved(self.alias)
        return self._account_id

    @property
    def session(self) -> boto3.Session:
        if not self._session:
            raise AccountNotResolved(self.alias)
        return self._session


class AccountNotResolved(Exception):
    def __init__(self, alias: str) -> None:
        super().__init__(f"account {alias=} is not resolved")


def timeit(method) -> Callable:
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = method(*args, **kwargs)
        end_time = time.time()
        print(f"{method.__name__} => {(end_time - start_time) * 1000} ms")

        return result

    return wrapper


@lru_cache
def argv_help() -> bool:
    return any([v in FLAGS_HELP for v in sys.argv])


@lru_cache
def argv_dry_run() -> bool:
    return any([v in FLAGS_DRY_RUN for v in sys.argv])


@lru_cache
def argv_filtered() -> List[str]:
    return sorted(set(sys.argv[1:]) - set(FLAGS_HELP + FLAGS_DRY_RUN))


@lru_cache
def extract_region(alias: str) -> str:
    assert alias, "expecting non empty string"
    code = alias.split("-", 1)[0]

    assert code in AWS_REGIONS, f"could not detect region from {alias=}"

    return AWS_REGIONS[code]


@lru_cache
def extract_profile(alias: str) -> str:
    assert alias, "expecting non empty string"
    return f"{alias}{AWS_PROFILE_SUFFIX}"


@lru_cache
def extract_ce_id(value: str) -> Optional[str]:
    try:
        result = re.match(CE_REGEX, value, re.IGNORECASE)

        if not result:
            return None

        return result.groups()[0].upper()
    except Exception:
        return None


@lru_cache
def session_factory(profile: str, region: str) -> boto3.Session:
    _log.debug(f"boto3 session [{profile=}, {region=}] ...")

    return boto3.Session(profile_name=profile, region_name=region)


def get_regions(session: boto3.Session) -> List[str]:
    _log.debug("loading regions ...")
    response = session.client("ec2").describe_regions()
    return [item.get("RegionName", "") for item in response.get("Regions", [])]


@lru_cache
def resolve_account(alias: str) -> Account:
    alias = alias.strip()
    _log.info(f"[{alias}] resolving account ...")

    account_id = ""
    profile = extract_profile(alias)
    region = extract_region(alias)

    try:
        session = session_factory(profile, region)

        account_id = session.client("sts").get_caller_identity()["Account"]
    except (botocore.exceptions.ClientError, botocore.exceptions.ProfileNotFound):
        session = None

    return Account(alias, region, profile, account_id, session)


@timeit
def resolve_accounts(aliases: List[str]) -> List[Account]:
    accounts = run_threaded(resolve_account, aliases, threads=10, timeout=15)

    missing_profiles = [account.profile for account in accounts if not account.resolved]
    missing_aliases = [account.alias for account in accounts if not account.resolved]

    if missing_profiles:
        print(
            f"Error: following account(s) could not be resolved: {','.join(missing_aliases)}",
            file=sys.stderr,
        )
        print("Refresh credentials with command:", file=sys.stderr)
        print()
        print(
            f'"${{AWSCONNECT_DIR}}/awsconnect" --role {" --role ".join(missing_profiles)}',
            file=sys.stderr,
        )
        print()
        print("And try again!", file=sys.stderr)
        sys.exit(1)

    print()
    print(f"Resolved {len(accounts)} accounts:")

    for account in accounts:
        print(f" - {account.alias} : {account.account_id} / {account.region}")

    return accounts


def run_threaded(fn, iterable, threads: int = 10, timeout: float = 60) -> List:
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as tpe:
        return list(tpe.map(fn, iterable, timeout=timeout))


# def run_threaded(
#     tasks: Iterable[Callable[[], None]],
#     max_workers: int,
#     timeout: float = None,
#     thread_name_prefix: str = "",
# ):
#     assert max_workers >= 1, f"Expecting num_threads >= 1, got {max_workers!r} instead."

#     cancelled = threading.Event()

#     if timeout is not None:
#         assert timeout > 0.0, f"Expecting timeout > 0.0, got {timeout!r} instead."
#         timer = threading.Timer(interval=timeout, function=cancelled.set)
#         timer.setDaemon(True)
#         timer.start()

#     _log.debug(f"starting with {max_workers} threads ...")

#     tasks = iter(tasks)

#     items_done = 0

#     futures = {}

#     with concurrent.futures.ThreadPoolExecutor(
#         max_workers=max_workers, thread_name_prefix=thread_name_prefix
#     ) as tpe:
#         for task in itertools.islice(tasks, max_workers):
#             # add, not overwrite
#             future = tpe.submit(task)
#             futures[future] = task

#         while len(futures):
#             done, _ = concurrent.futures.wait(
#                 futures, return_when=concurrent.futures.FIRST_COMPLETED
#             )

#             for future in done:
#                 items_done += 1
#                 del futures[future]

#             if cancelled.is_set():
#                 _log.warning("cancel by timeout ...")
#                 break

#             for task in itertools.islice(tasks, max_workers - len(futures)):
#                 future = tpe.submit(task)
#                 futures[future] = True

#         _log.debug("gracefully shutting down ...")

#     for future in futures.copy():
#         if future.done():
#             items_done += 1

#         del futures[future]

#     _log.debug("shut down")

#     return (not cancelled.is_set(), items_done)
