import aioboto3
import csv
import asyncio
from botocore.exceptions import ClientError

SPOKE_ROLE = "CIP_INSPECTOR"
CSV_FILENAME = "role_data.csv"
METADATA_TABLE = "WH-0003-DYN_METADATA"
csv_lock = asyncio.Lock()


async def fetch_roles_in_account(session, account_id, account_name, writer, spoke_meta):
    async def process_role(iam, role):
        role_details = await iam.get_role(RoleName=role["RoleName"])
        last_used = role_details["Role"].get("RoleLastUsed", {}).get("LastUsedDate", "")
        boundary_policy = (
            role_details["Role"]
            .get("PermissionsBoundary", {})
            .get("PermissionsBoundaryArn", "")
        )
        async with csv_lock:
            writer.writerow(
                {
                    "SpokeName": account_name,
                    "AccountID": account_id,
                    "RoleName": role["RoleName"],
                    "BoundaryPolicy": boundary_policy,
                    "LastUsed": last_used,
                    "NetworkType": spoke_meta.get(account_id, {}).get("networkType"),
                    "EnvironmentType": spoke_meta.get(account_id, {}).get(
                        "environmentType"
                    ),
                    "Region": spoke_meta.get(account_id, {}).get("region"),
                    "InternetFacing": spoke_meta.get(account_id, {}).get(
                        "internetFacing"
                    ),
                    "Status": spoke_meta.get(account_id, {}).get("status"),
                }
            )

    print("analysing account", account_name)
    async with session.client("sts") as sts:
        try:
            assumed_role_object = await sts.assume_role(
                RoleArn=f"arn:aws:iam::{account_id}:role/{SPOKE_ROLE}",
                RoleSessionName="InvestigateBoundaryPoliciesSession",
            )
            credentials = assumed_role_object["Credentials"]
        except ClientError:
            print(account_name, "Error assuming role, skipping")
            async with csv_lock:
                writer.writerow(
                    {
                        "SpokeName": account_name,
                        "AccountID": account_id,
                        "RoleName": "Error Assuming Role",
                    }
                )
            return

    async with session.client(
        "iam",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    ) as iam:
        paginator = iam.get_paginator("list_roles")
        async for page in paginator.paginate():
            tasks = [process_role(iam, role) for role in page["Roles"]]
            await asyncio.gather(*tasks)


async def get_spoke_metadata(session):
    print(f"Scanning over DDB table: {METADATA_TABLE}")
    async with session.resource("dynamodb") as dynamodb:
        metadata_table = await dynamodb.Table(METADATA_TABLE)
        params = {}
        results = {}
        while True:
            try:
                response = await metadata_table.scan(**params)
            except Exception as e:
                print(f"Error scanning DynamoDB table: {e}")
                break
            for item in response.get("Items", []):
                account_id = item.get("account")
                results[account_id] = {
                    "accountName": item.get("account-name"),
                    "account": account_id,
                    "status": item.get("status"),
                    "internetFacing": item.get("internet-facing"),
                    "region": item.get("region"),
                    "environmentType": item.get("environment-type"),
                    "networkType": item.get("network-type"),
                }
            if "LastEvaluatedKey" not in response:
                break
            params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return results


async def main():
    session = aioboto3.Session()
    spoke_meta = await get_spoke_metadata(session)
    fieldnames = [
        "SpokeName",
        "AccountID",
        "RoleName",
        "BoundaryPolicy",
        "LastUsed",
        "NetworkType",
        "EnvironmentType",
        "Region",
        "InternetFacing",
        "Status",
    ]
    async with session.client("sts") as sts:
        hub_account_id = (await sts.get_caller_identity()).get("Account")
    with open(CSV_FILENAME, "a", newline="", encoding="UTF-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        async with session.client("organizations") as client:
            paginator = client.get_paginator("list_accounts")
            async for page in paginator.paginate():
                tasks = [
                    fetch_roles_in_account(
                        session, account["Id"], account["Name"], writer, spoke_meta
                    )
                    for account in page["Accounts"]
                    if account["Status"] == "ACTIVE"
                    and account["Id"] != hub_account_id
                    and account["Id"]
                ]
                await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
