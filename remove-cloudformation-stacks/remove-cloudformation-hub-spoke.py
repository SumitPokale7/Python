
from botocore.exceptions import ClientError
import asyncio
import aiobotocore.session
import logging
from botocore.parsers import ResponseParserError

logging.basicConfig(
    filename="./remove-cfn-hs.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="WARN",
)
logger = logging.getLogger("boto3")

DISABLED_REGIONS = {
    "ap-south-1",
    "eu-north-1",
    "eu-west-3",
    "ap-northeast-3",
    "ap-northeast-2",
    "ap-northeast-1",
    "ca-central-1",
    "sa-east-1",
    "us-west-1",
    "us-west-2",
}
ROLE_NAME = "AWS_PLATFORM_ADMIN"


async def assume_role(account_id, region, client_type):
    session = aiobotocore.session.get_session()
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    async with session.create_client("sts") as sts_client:
        try:
            response = await sts_client.assume_role(RoleArn=role_arn, RoleSessionName=f"EKSSession{account_id}")
        except ResponseParserError:
            logger.warning("Response parser failure, retrying")
            return await assume_role(account_id, region, client_type)
        creds = response["Credentials"]
        return session.create_client(
            client_type,
            region_name=region,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )


async def write_line(line: str):
    with open("data.csv", "a") as f:
        f.write(line + "\n")


async def delete_cft(account: dict, region: str, dry_run: bool = True):
    """
    This methods deletes the cloudformation
    """
    logger.warning(f"Processing {account['id']} {account['name']}")
    stack_name = f"{account['name']}-CFN-AutoTaggerV3-Butler-Assets"
    try:
        cfn_client = await assume_role(account["id"], region, "cloudformation")
    except ClientError:
        logger.warning(f"Failed to assume role: {account['id']}")
        return
    logger.warning(f"Role Assumed: {account['name']}")
    async with cfn_client as client:
        try:
            if dry_run:
                try:
                    await client.describe_stacks(StackName=stack_name)
                except ClientError:
                    logger.warning(f"Stack not found {stack_name} in region {region}, continuing")
                    return
                await write_line(f"{account['id']},{account['name']},{region},{stack_name}")
            else:
                try:
                    await client.describe_stacks(StackName=stack_name)
                except ClientError:
                    logger.warning(f"Stack not found {stack_name} in region {region}, continuing")
                    return
                delete_cft_response = await client.delete_stack(StackName=stack_name)
                waiter = await client.get_waiter("stack_delete_complete")
                await waiter.wait(StackName=stack_name)
                logger.warning(
                    f"Deleted cft stack { stack_name } in region {region} delete cft response {delete_cft_response }"
                )

        except ClientError as err:
            logger.warning(f"Failed to delete the cft:\n {err}")
            raise err


async def get_organization_accounts():
    session = aiobotocore.session.get_session()
    async with session.create_client("organizations") as org_client:
        paginator = org_client.get_paginator("list_accounts")
        return [
            {"id": account["Id"], "name": account["Name"]}
            async for page in paginator.paginate()
            for account in page["Accounts"]
        ]


def chunk_list(lst: list, n: int):
    return (lst[i: i + n] for i in range(0, len(lst), n))


async def main(dry_run=True):
    await write_line("account_id,account_name,region,stack_name")
    account_data = await get_organization_accounts()
    account_chunks = chunk_list(account_data, 20)
    logger.warning("Accounts gathered, starting scan")
    for accounts in account_chunks:
        tasks = [delete_cft(account, region, dry_run) for region in DISABLED_REGIONS for account in accounts]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
