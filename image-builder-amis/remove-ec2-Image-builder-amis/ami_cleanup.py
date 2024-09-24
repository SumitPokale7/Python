import os
import sys
import time
import logging
import json
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    filename="./ami-cleanup-logfile.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))

# change hub name based on H1/H2/H3
hub_name = "WH-00H1"
print(hub_name)


lmb_spoke_account = {
    "WH-00H1": ["WS-Z0S4", 495416159460],
    "WH-00H2": ["WS-Y0MI", 974944152507],
    "WH-00H3": ["WS-01AW", 768961172930],
}


def assume_role():
    source_profile = f"{hub_name}-role_OPERATIONS"
    try:
        role_arn = (
            f"arn:aws:iam::{lmb_spoke_account[hub_name][1]}:role/AWS_PLATFORM_ADMIN"
        )
        role_session_name = "DELETE-AMI"
        session = boto3.Session(profile_name=source_profile)
        sts_client = session.client("sts")
        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
        return response["Credentials"]

    except Exception as e:
        logger.error(e)


def aws_session(region):
    credentials = assume_role()
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    )
    return session


ami_region = [
    "ap-south-1",
    "ap-northeast-3",
    "ap-northeast-2",
    "ap-northeast-1",
    "ca-central-1",
    "eu-west-3",
    "eu-north-1",
    "sa-east-1",
    "us-west-1",
    "us-west-2",
]


def delete_cft(stack_name: str, region: str, dry_run: bool = None):
    """
    This methods deletes the cloudformation
    """
    session = aws_session(region)
    client = session.client("cloudformation")
    try:
        if dry_run:
            logger.info(f"DRY RUN: Would have deleted cft stack { stack_name }")
            try:
                client.describe_stacks(StackName=stack_name)

            except ClientError:
                logger.warning(
                    f"Stack not found {stack_name} in region {region}, continuing"
                )
            return
        else:
            try:
                client.describe_stacks(StackName=stack_name)
            except ClientError:
                logger.warning(
                    f"Stack not found {stack_name} in region {region}, continuing"
                )
                return
            delete_cft_response = client.delete_stack(StackName=stack_name)
            waiter = client.get_waiter("stack_delete_complete")
            waiter.wait(StackName=stack_name)
            logger.info(
                f"Deleted cft stack { stack_name } delete cft response  {delete_cft_response }"
            )

    except ClientError as err:
        logger.error(f"Failed to delete the cft:\n {err}")
        raise err


def get_instance_info(ami_id, region):
    """
    Get AMI ID from AMI

    Parameters
    ebs_mapping: EBS Mapping
    """
    session = aws_session(region)
    ec2_client = session.client("ec2")
    response = ec2_client.describe_instances(
        Filters=[{"Name": "image-id", "Values": [ami_id]}]
    )

    # Check if there are any instances running with the specified AMI
    instances = response["Reservations"]
    if instances:
        print("AMI is running as instance:", ami_id)
        for instance in instances:
            # print("Instance ID:", instance["Instances"][0]["InstanceId"])
            logger.info(
                f"AMI is running as instance: { instance['Instances'][0]['InstanceId'] } in {region} AMI-ID: {ami_id}"
            )
        return True
    else:
        return False


def get_snapid_from_ami(ebs_mapping):
    """
    Get Snapshot ID from AMI

    Parameters
    ebs_mapping: EBS Mapping
    """
    return [
        snapshot["Ebs"]["SnapshotId"] for snapshot in ebs_mapping if "Ebs" in snapshot
    ]


def deregister_ami(ami_id, region):
    """
    De-Register AMI

    Parameters
    ami_id: AMI ID
    region: AWS Region
    """
    return aws_session(region).resource("ec2").Image(ami_id).deregister()


def delete_snapshot(snapshot_id, region):
    """
    Delete Snapshot

    Parameters
    snapshot_id: EBS Snapshot ID
    region: AWS Region
    """
    for snap in snapshot_id:
        aws_session(region).resource("ec2").Snapshot(snap).delete()
    return True


def cleanup_amis(dry_run=None):
    """
    Cleanup AMI
    """
    filters = [{"Name": "tag:CreatedBy", "Values": ["EC2 Image Builder"]}]
    for region in ami_region:
        logger.info(f"Getting AMI(s) in {region} tagged as {filters}")
        try:
            response = (
                aws_session(region)
                .client("ec2")
                .describe_images(Owners=["self"], Filters=filters)
            )
            logger.info(
                f"""Number of AMI(s) in {region}: {len(response['Images'])}\n"""
            )
            logger.debug(
                f"""Describe AMI on filters Response:
                {json.dumps(response, indent=4, default=str)}"""
            )
            if not dry_run:
                for amis in response["Images"]:
                    flag = get_instance_info(amis["ImageId"], region)
                    if flag is False:
                        response_js = {
                            amis["ImageId"]: get_snapid_from_ami(
                                amis["BlockDeviceMappings"]
                            )
                        }
                        logger.debug(
                            f"""Mapping AMI EBS Snapshot(s):
                            {json.dumps(response_js, indent=4, default=str)}\n"""
                        )
                        logger.info(f"Deregistering {amis['ImageId']}")
                        time.sleep(3)
                        try:
                            deregister_ami(amis["ImageId"], region)
                        except ClientError as error:
                            logger.error(f"Error with AMI:{amis['ImageId']}\n{error}")
                        logger.info(
                            f"""Deleting {amis['ImageId']}'s snapshot(s){response_js[amis['ImageId']]}"""
                        )
                        time.sleep(3)
                        try:
                            if delete_snapshot(response_js[amis["ImageId"]], region):
                                logger.info("Operation Completed!\n")

                        except ClientError as error:
                            logger.error(
                                f"Error with snapshot: {response_js[amis['ImageId']]}\n{error}"
                            )

            get_keys(region)  # backup keys
            remove_stack(region, dry_run)  # remove CFN called
            get_ssm_documents(region, dry_run)  # unshared ssm documents

        except Exception as err:
            logger.error(err)


def remove_stack(region, dry_run):
    # WS-Z0S4    H1
    # WS-Y0MI    H2
    # WS-01AW    H3
    account = (lmb_spoke_account[hub_name][0])
    stack_name = "IMAGE-BUILDER-KMS-REPLICA"
    stack_to_be_deleted = f"{account}-{stack_name}"
    delete_cft(stack_to_be_deleted, region, dry_run)


def get_keys(region):
    session = aws_session(region)
    client = session.client("kms")
    response = client.list_keys()

    customer_managed_key_names = []
    for key in response["Keys"]:
        key_id = key["KeyId"]
        key_metadata = client.describe_key(KeyId=key_id)

        # Check if the key is customer-managed
        if key_metadata["KeyMetadata"]["KeyManager"] == "CUSTOMER":
            customer_managed_key_names.append(key_id)

    for key_name in customer_managed_key_names:
        # print(key_name)
        retrieve_normalised_policy(key_name, region)


def retrieve_normalised_policy(keyid, region):
    session = aws_session(region)
    client = session.client("kms")
    key = client.describe_key(KeyId=keyid)

    policy = json.loads(
        client.get_key_policy(KeyId=key["KeyMetadata"]["KeyId"], PolicyName="default")[
            "Policy"
        ]
    )

    for sid in policy["Statement"]:
        if type(sid["Action"]) == list:
            sid["Action"].sort()
        if "AWS" in sid["Principal"]:
            if type(sid["Principal"]["AWS"]) == list:
                sid["Principal"]["AWS"].sort()

    dump_to_file(policy, keyid, region)


# restore key from backup
def push_to_server(region, keyid):
    session = aws_session(region)
    account = lmb_spoke_account[hub_name][1]
    key_name = "WS-Z0S4-IB-MR-KMS"  # changed as needed
    path = f"./kms_backup/{account}/{region}/{key_name}/"

    with open("{}/{}.json".format(path, keyid), "r") as infile:
        policy = json.load(infile)

    client = session.client("kms")
    key = client.describe_key(KeyId=keyid)
    full_policy = client.get_key_policy(
        KeyId=key["KeyMetadata"]["KeyId"], PolicyName="default"
    )
    full_policy["Policy"] = policy
    try:
        client.put_key_policy(
            KeyId=key["KeyMetadata"]["KeyId"],
            PolicyName="default",
            Policy=json.dumps(policy),
        )
    except Exception as e:
        raise e


def dump_to_file(policy, keyid, region):
    key_name = policy["Id"]
    account = lmb_spoke_account[hub_name][1]
    path = set_file_path(account, region, key_name)

    with open("{}/{}.json".format(path, keyid), "w") as outfile:
        json.dump(policy, outfile, indent=4, sort_keys=True)
        outfile.close()
    logger.info(f"KMS Policy saved for {region} on {path}")


def set_file_path(account, region, key_name=None):
    path = f"./ssm_backup/{account}/{region}"
    if key_name:
        path = f"./kms_backup/{account}/{region}/{key_name}"
    try:
        os.makedirs(path)

    except OSError:  # Python >2.5
        if OSError.errno != 1:
            pass
        else:
            raise
    return path


def get_ssm_documents(region, dry_run=None):
    session = aws_session(region)
    ssm_client = session.client("ssm")
    filters = [
        {"Key": "Owner", "Values": ["self"]},
        {
            "Key": "Name",
            "Values": ["BpPlatformServices"],
        },
    ]
    response = ssm_client.list_documents(Filters=filters)
    for document in response["DocumentIdentifiers"]:
        dox = document["Name"]
        logger.info(f"Getting DOCS(s) in {region} Name: {dox}")
        response = ssm_client.describe_document_permission(
            Name=dox, PermissionType="Share"
        )
        response_content = ssm_client.get_document(Name=dox, DocumentFormat="YAML")
        policy = response_content["Content"]
        account = lmb_spoke_account[hub_name][1]
        path = set_file_path(account, region)
        with open("{}/{}.yaml".format(path, dox), "w") as outfile:
            outfile.write(policy)
            outfile.close()
        logger.info(f"ssm document: {dox} saved for {region}")

        AccountIds = response["AccountIds"]
        if not dry_run:
            for account_id in AccountIds:
                # print(account_id)
                ssm_client.modify_document_permission(
                    Name=dox,
                    PermissionType="Share",
                    AccountIdsToAdd=[],
                    AccountIdsToRemove=[account_id],
                )
            logger.info(f"Deleteing DOCS(s) in {region} Name: {dox}")
            ssm_client.delete_document(Name=dox)


cleanup_amis()

# example how to push kms back
# push_to_server("ap-south-1","mrk-af71795c16fc4c28a4cd551bc8db1ac9")
