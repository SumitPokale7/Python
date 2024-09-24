import asyncio
import time
import aiobotocore.session
import csv

DISABLED_REGIONS = {
    "ap-south-1", "eu-north-1", "eu-west-3", "ap-northeast-3",
    "ap-northeast-2", "ap-northeast-1", "ca-central-1",
    "sa-east-1", "us-west-1", "us-west-2"
}
ASSUME_ROLE = "AWS_PLATFORM_ADMIN"
EKS_MANAGEMENT_ROLE = "WizAccess-Role"


async def get_enabled_regions():
    session = aiobotocore.session.get_session()
    async with session.create_client("ec2") as ec2_client:
        regions = await ec2_client.describe_regions()
        return [region["RegionName"] for region in regions["Regions"]
                if region["RegionName"] not in DISABLED_REGIONS]


async def assume_role(account_id, region):
    session = aiobotocore.session.get_session()
    role_arn = f"arn:aws:iam::{account_id}:role/{ASSUME_ROLE}"
    async with session.create_client("sts") as sts_client:
        response = await sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"EKSSession{account_id}")
        creds = response["Credentials"]
        return session.create_client(
            "eks", region_name=region,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"])


async def wait_for_update_completion(client, cluster_name: str, update_id: str) -> bool:
    while True:
        try:
            req = await client.describe_update(name=cluster_name, updateId=update_id)
            status = req["update"]["status"]
            if status == "Successful":
                return True
            elif status == "InProgress":
                time.sleep(15)
            else:
                raise Exception(f"Cluster in unexpected status: {status}")
        except aiobotocore.exceptions.ClientError as e:
            raise Exception(f"Error checking cluster status: {e}")


async def update_eks_authentication(eks_client, cluster_name, account_id):
    try:
        cluster = await eks_client.describe_cluster(name=cluster_name)
        authentication_mode = cluster.get("cluster", {}).get("accessConfig", {}).get("authenticationMode")
        status = cluster.get("cluster", {}).get("status", {})
        if authentication_mode == "CONFIG_MAP" and status == "ACTIVE":
            response = await eks_client.update_cluster_config(
                name=cluster_name, accessConfig={"authenticationMode": "API_AND_CONFIG_MAP"}
            )
            await wait_for_update_completion(eks_client, cluster_name, response["update"]["id"])
            print(f"Successfully updated cluster {cluster_name}")
        else:
            print(f"Skipped updating cluster {cluster_name}")
        response = await eks_client.associate_access_policy(
            clusterName=cluster_name,
            principalArn=f"arn:aws:iam::{account_id}:role/{EKS_MANAGEMENT_ROLE}",
            policyArn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
            accessScope={"type": "cluster"},
        )
        print(f"Updated Access policies for {cluster_name}")
    except Exception as e:
        print(f"Failed to update cluster {cluster_name}: {e}")


async def list_and_update_clusters(account_id, region):
    print(f"Scanning: {account_id} - {region}")
    tasks = []
    try:
        eks_client = await assume_role(account_id, region)
        async with eks_client as client:
            clusters = (await client.list_clusters())["clusters"]
            if not clusters:
                await write_line(f"{account_id},{region},")
            for cluster in clusters:
                await write_line(f"{account_id},{region},{cluster}")
                tasks.append(update_eks_authentication(client, cluster, account_id))
            await asyncio.gather(*tasks)
    except Exception as e:
        print(e)


async def get_organization_account_ids():
    session = aiobotocore.session.get_session()
    async with session.create_client("organizations") as org_client:
        paginator = org_client.get_paginator("list_accounts")
        return [account["Id"] async for page in paginator.paginate() for account in page["Accounts"]]


async def write_line(line: str):
    with open("data.csv", "a") as f:
        f.write(line + "\n")


async def read_csv():
    account_ids = {}
    with open("data.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                account_id = row[0]
                region = row[1] if len(row) > 1 else None
                account_ids.setdefault(region, []).append(account_id)
    return account_ids


def chunk_list(lst: list, n: int):
    return (lst[i: i + n] for i in range(0, len(lst), n))


async def main():
    await write_line("account_id,region,clusters")
    already_scanned = await read_csv()
    account_ids = await get_organization_account_ids()
    account_chunks = chunk_list(account_ids, 20)
    print("Accounts gathered, starting scan")
    enabled_regions = await get_enabled_regions()
    tasks = [list_and_update_clusters(account_id, region)
             for accounts in account_chunks
             for region in enabled_regions
             for account_id in accounts
             if account_id not in already_scanned.get(region, [])]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
