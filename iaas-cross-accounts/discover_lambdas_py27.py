#!/usr/bin/env python3

import itertools
import json
import logging
import os
import random
import sys
from typing import List
from datetime import datetime, timedelta, timezone

import lib

_log = logging.getLogger("cli")

SELF_FILENAME = os.path.basename(__file__)
REPORT_FILENAME = os.path.abspath(f"{os.path.splitext(SELF_FILENAME)[0]}.report.json")


def usage():
    print(f"Usage: ./{SELF_FILENAME} <account>[ <account>]")
    print()
    print("Arguments:")
    print("    account          - account alias, such as AccountName-A1")
    print()
    print("Parameters:")
    print("    -h, --help       - display help")
    print()


def main():
    if lib.argv_help():
        usage()
        exit(0)

    account_aliases = lib.argv_filtered()

    if not account_aliases:
        print("Error: provide at least one account name.")
        usage()
        sys.exit(1)

    print("Starting ...")

    accounts = lib.resolve_accounts(account_aliases)

    print()
    input("Proceed? <Ctrl-C> to abort ... ")
    print()

    discover_all_lambdas(accounts)

    print("DONE")


@lib.timeit
def discover_all_lambdas(accounts: List[lib.Account]):
    lambdas = lib.run_threaded(discover_lambdas, accounts, threads=10, timeout=600)
    flatten = list(itertools.chain.from_iterable(lambdas))

    _log.info(f"totally found {len(flatten)} functions in {len(lambdas)} accounts")

    try:
        os.mkdir(os.path.dirname(REPORT_FILENAME))
    except FileExistsError:
        pass

    with open(REPORT_FILENAME, "w") as fp:
        json.dump(flatten, fp, indent=2)

    _log.info(f"report is stored in {REPORT_FILENAME!r} file")


def check_execution_period(execution_date: object, past_months: int) -> bool:
    today = datetime.now().astimezone(timezone.utc)
    edge_date = today - timedelta(days=past_months * 30)
    if edge_date < execution_date < today:
        return True
    return False


def find_event_rules(client: object, function_arn: str) -> list:
    try:
        described_event_rules = []

        event_rules = (
            client.get_paginator("list_rule_names_by_target")
            .paginate(TargetArn=function_arn)
            .build_full_result()
            .get("RuleNames", [])
        )

        deduplicated_event_rules = list(set(event_rules))

        for event_rule in deduplicated_event_rules:
            status = client.describe_rule(Name=event_rule).get("State")
            described_event_rules.append({event_rule: status})

    except Exception:
        described_event_rules = []
    return described_event_rules


def find_event_source_mappings(client: object, function_arn: str) -> list:
    try:
        event_source_arns = []

        event_source_mappings = client.list_event_source_mappings(
            FunctionName=function_arn
        ).get("EventSourceMappings", [])

        for event_source_mapping in event_source_mappings:
            event_source_arns.append(event_source_mapping.get("EventSourceArn", ""))

    except Exception:
        event_source_arns = []

    return event_source_arns


def find_last_execution_time(client: object, function_name: str) -> object:
    try:
        log_streams = client.describe_log_streams(
            logGroupName=f"/aws/lambda/{function_name}",
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        ).get("logStreams")

        for log_stream in log_streams:
            last_event_unix_time = log_stream.get("lastEventTimestamp", None)

        last_event_time = datetime.fromtimestamp(
            last_event_unix_time / 1000
        ).astimezone(timezone.utc)

    except Exception:
        last_event_time = None

    return last_event_time


@lib.timeit
def discover_lambdas(account: lib.Account) -> List[dict]:
    regions = lib.get_regions(account.session)
    random.shuffle(regions)

    funcs = []

    for region in regions:
        _log.info(f"[{account.alias}] loading function in {region} ...")

        client = account.session.client("lambda", region_name=region)
        events_client = account.session.client("events", region_name=region)
        logs_client = account.session.client("logs", region_name=region)

        items = client.get_paginator("list_functions").paginate().build_full_result()

        found = 0

        for item in items.get("Functions", []):
            if not item["Runtime"].startswith("python2"):
                continue

            found += 1

            tags = client.list_tags(Resource=item["FunctionArn"]).get("Tags", [])

            event_rules = find_event_rules(events_client, item["FunctionArn"])

            event_source_arns = find_event_source_mappings(client, item["FunctionArn"])

            last_executed = find_last_execution_time(logs_client, item["FunctionName"])

            if last_executed:
                executed_within_3_months = check_execution_period(
                    last_executed, past_months=3
                )
                executed_within_6_months = check_execution_period(
                    last_executed, past_months=6
                )
            else:
                executed_within_3_months = False
                executed_within_6_months = False

            ce_id = None

            if tags.get("cloud-environment"):
                ce_id = tags["cloud-environment"]

            if not ce_id and tags.get("aws:cloudformation:stack-name"):
                ce_id = lib.extract_ce_id(tags["aws:cloudformation:stack-name"])

            if not ce_id:
                ce_id = lib.extract_ce_id(item["FunctionName"])

            sanitized_name = (
                item["FunctionName"]
                .replace(account.alias, "<ALIAS>")
                .replace(account.alias.replace("-", ""), "<ALIAS>")
            )

            if "-" in sanitized_name:
                parts = sanitized_name.split("-")

                if (
                    len(parts[-1]) > 10
                    and "_" not in parts[-1]
                    and parts[-1] == parts[-1].upper()
                ):
                    parts[-1] = "<RANDOM>"
                    sanitized_name = "-".join(parts)

            funcs.append(
                {
                    "AccountAlias": account.alias,
                    "AccountId": account.account_id,
                    "Region": region,
                    "CeId": ce_id,
                    "FunctionArn": item["FunctionArn"],
                    "FunctionName": item["FunctionName"],
                    "SanitizedName": sanitized_name,
                    "Description": item["Description"].strip() or None,
                    "LastModified": item["LastModified"],
                    "LayerArns": [layer["Arn"] for layer in item.get("Layers", [])],
                    "MemorySize": item["MemorySize"],
                    "Runtime": item["Runtime"],
                    "Timeout": item["Timeout"],
                    "Tags": tags,
                    "EventRulesNames": event_rules,
                    "EventSourceArns": event_source_arns,
                    "LastExecutionTime": last_executed.isoformat(
                        timespec="milliseconds"
                    )
                    if last_executed
                    else None,
                    "ExecutedWithin3Months": executed_within_3_months,
                    "ExecutedWithin6Months": executed_within_6_months,
                }
            )

        _log.info(f"[{account.alias}] found {found} functions in {region}")

    return funcs


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Aborted, bye.")
        exit(130)
