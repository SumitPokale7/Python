from botocore.exceptions import ClientError
import boto3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


LONG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def create_creds(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="LambdaInventorySession"
    )


def create_client(
    service: str, role: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        creds = create_creds(role, hub_session)
        client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"cannot assume the role: {e}")
        raise e

    return client


def convert_date_str(date_, format_=LONG_DATE_FORMAT):
    """Convert date to string"""
    date_str = date_.strftime(format_)
    return date_str


def extract_functions(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    _extract_logs: str = "NO",
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            lambda_client = create_client("lambda", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            lambda_client = session.client("lambda")

        paginator = lambda_client.get_paginator("list_functions")
        response_iterator = paginator.paginate(PaginationConfig={"PageSize": max_item})

        return [
            {
                "function_name": one_function["FunctionName"],
                "runtime": one_function["Runtime"]
                if "Runtime" in one_function
                else "NA",
                "code_size(kb)": one_function["CodeSize"] / 1024,
                "memory_size": one_function["MemorySize"],
                "function_arn": one_function["FunctionArn"],
                "last_modification": one_function["LastModified"],
                "account_id": _account_id,
                "last_execution": extract_logs(
                    session, one_function["FunctionName"], _account_id
                )
                if _extract_logs == "YES"
                else "Na",
            }
            for response in response_iterator
            for one_function in response["Functions"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_roles(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            iam_client = create_client("iam", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            iam_client = session.client("iam")

        paginator = iam_client.get_paginator("list_roles")
        response_iterator = paginator.paginate(PaginationConfig={"PageSize": max_item})

        return [
            {
                "rolename": one_role["RoleName"],
                "Arn": one_role["Arn"],
                "trust-relationship": one_role["AssumeRolePolicyDocument"],
            }
            for response in response_iterator
            for one_role in response["Roles"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_vpcs(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    key_tag_name: str = None,
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ec2_client = create_client("ec2", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            ec2_client = session.client("ec2")

        paginator = ec2_client.get_paginator("describe_vpcs")
        response_iterator = paginator.paginate(PaginationConfig={"PageSize": max_item})

        return [
            {
                "account_id": _account_id,
                "vpc_id": response_vpc["VpcId"],
                "tags": response_vpc["Tags"],
            }
            for response in response_iterator
            for response_vpc in response["Vpcs"]
            for one_tag in response_vpc["Tags"]
            if key_tag_name in one_tag["Key"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_fws(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            fw_client = create_client(
                "network-firewall", target_role_arn, _region, session
            )
        # iterate over only hub account
        else:
            fw_client = session.client("network-firewall")

        paginator = fw_client.get_paginator("list_firewall_policies")
        response_iterator = paginator.paginate(PaginationConfig={"PageSize": max_item})

        return [
            {
                "firewall_name": response["FirewallName"],
                "firewall_arn": response["FirewallArn"],
            }
            for response in response_iterator
            for response in response["Firewalls"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_kms(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ec2_boto_client = create_client("ec2", target_role_arn, _region, session)
            key_client = create_client("kms", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            ec2_boto_client = session.client("ec2")
            key_client = session.client("kms")

        volume_paginator = ec2_boto_client.get_paginator("describe_volumes")
        volume_iterator = volume_paginator.paginate(
            PaginationConfig={"PageSize": max_item}
        )

        volumes = []
        for response in volume_iterator:
            for one in response["Volumes"]:
                try:
                    volume = session.resource("ec2").Volume(one["VolumeId"])
                    if volume.kms_key_id:
                        response = key_client.list_aliases(
                            KeyId=volume.kms_key_id[volume.kms_key_id.find("/") + 1:]
                        )
                    else:
                        response["Aliases"] = []

                except ClientError as err:
                    if err.response["Error"]["Code"] == "InvalidVolume.NotFound":
                        logger.warning(
                            f"cannot found {one['VolumeId']} because of {err.response['Error']['Message']}"
                        )
                    else:
                        raise err

                volumes.append(
                    {
                        "instance": one["Attachments"][0]["InstanceId"]
                        if len(one["Attachments"]) > 0
                        else "not attached",
                        "volume": volume.volume_id,
                        "state": volume.state,
                        "aliases": ",".join(
                            [
                                one_alias["AliasName"]
                                for one_alias in response["Aliases"]
                            ]
                        ),
                    }
                )

        return volumes

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_logs(
    session: boto3.session.Session,
    function_name: str,
    _account_id: str = None,
    _region: str = "eu-west-1",
    max_item: int = 50,
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            logs_client = create_client("logs", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            logs_client = session.client("logs")

        paginator = logs_client.get_paginator("describe_log_groups")
        response_iterator = paginator.paginate(
            logGroupNamePrefix=f"/aws/lambda/{function_name}",
            PaginationConfig={"PageSize": max_item},
        )

        for response in response_iterator:
            one_list = response["logGroups"]
            for one_group in one_list:
                paginator_streams = logs_client.get_paginator("describe_log_streams")
                logevent_iterator = paginator_streams.paginate(
                    logGroupName=one_group["logGroupName"],
                    orderBy="LastEventTime",
                    descending=True,
                    PaginationConfig={"PageSize": max_item},
                    limit=10,
                )
                for logevent in logevent_iterator:
                    last_streams = []
                    for event_stream in logevent["logStreams"][0:2]:
                        if "lastEventTimestamp" in event_stream:
                            dt_obj = datetime.datetime.fromtimestamp(
                                event_stream["lastEventTimestamp"] / 1000
                            )
                            last_streams.append(convert_date_str(dt_obj))

                        else:
                            print(event_stream)
                            last_streams.append("1981-01-01T00:00:00")

                    return "--".join(last_streams)

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def get_last_log_event(logs_client, log_group_name):
    try:
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )
        if "logStreams" in response and response["logStreams"]:
            log_stream_name = response["logStreams"][0]["logStreamName"]
            log_events_response = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                limit=1,
                startFromHead=True,
            )
            if "events" in log_events_response and log_events_response["events"]:
                last_log_timestamp = (
                    log_events_response["events"][0]["timestamp"] / 1000
                )
                last_log_time = datetime.fromtimestamp(last_log_timestamp)
                return last_log_time

        return "No log events found in the log group"
    except Exception as e:
        return str(e)


def extract_log_groups(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    max_item: int = 50,
):
    try:
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            logs_client = create_client("logs", target_role_arn, _region, session)
        else:
            logs_client = session.client("logs")

        paginator = logs_client.get_paginator("describe_log_groups")
        response_iterator = paginator.paginate(
            # Find single Pattern
            # logGroupNamePattern="DsServices_CWLogs_Host_Linux",
            PaginationConfig={"PageSize": max_item},
        )
        lg = []
        for response in response_iterator:
            for one in response["logGroups"]:
                seconds_since_epoch = one["creationTime"] / 1000.0
                timestamp = datetime.utcfromtimestamp(seconds_since_epoch)
                total_size_kb_bytes = one["storedBytes"] / 1000.0
                last_log_time = get_last_log_event(logs_client, one["logGroupName"])
                if last_log_time:
                    last_event_date = last_log_time
                else:
                    last_event_date = "no events"
                if "retentionInDays" in one:
                    lg.append(
                        {
                            "log_group_name": one["logGroupName"],
                            "creation": timestamp,
                            "retentionDays": one["retentionInDays"],
                            "Size in KB": total_size_kb_bytes,
                            "last_stream_date": last_event_date,
                        }
                    )
                else:
                    lg.append(
                        {
                            "log_group_name": one["logGroupName"],
                            "creation": timestamp,
                            "retentionDays": "No Retention Setup",
                            "Size in KB": total_size_kb_bytes,
                            "last_stream_date": last_event_date,
                        }
                    )
        return lg
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_sns(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            sns_client = create_client("sns", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            sns_client = session.client("sns")

        paginator = sns_client.get_paginator("list_topics")
        response_iterator = paginator.paginate()
        return [
            {"topic_arn": response["TopicArn"]}
            for response in response_iterator
            for response in response["Topics"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_portfolios(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            sc_client = create_client(
                "servicecatalog", target_role_arn, _region, session
            )
        # iterate over only hub account
        else:
            sc_client = session.client("servicecatalog")

        paginator = sc_client.get_paginator("list_accepted_portfolio_shares")
        operation_parameters = {
            "PortfolioShareType": "AWS_ORGANIZATIONS",
            "PageSize": 20,
        }
        response_iterator = paginator.paginate(**operation_parameters)
        return [
            {
                "AccountID": _account_id,
                "PortfolioName": response["DisplayName"],
                "Id": response["Id"],
                "Region": _region,
            }
            for response in response_iterator
            for response in response["PortfolioDetails"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_cloud_formations(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            cf_client = create_client(
                "cloudformation", target_role_arn, _region, session
            )
        # iterate over only hub account
        else:
            cf_client = session.client("cloudformation")

            # cloudformation stacks:
        cf_resources = []
        paginator = cf_client.get_paginator("list_stacks")
        inner_paginator = cf_client.get_paginator("list_stack_resources")
        response_iterator = paginator.paginate(StackStatusFilter=["CREATE_COMPLETE"])

        for response in response_iterator:
            for response_stack in response["StackSummaries"]:
                try:
                    inner_response_iterator = inner_paginator.paginate(
                        StackName=response_stack["StackName"]
                    )
                    cf_dict = {"stack_name": response_stack["StackName"]}

                    for inner_response in inner_response_iterator:
                        for inner_stack in inner_response["StackResourceSummaries"]:
                            if inner_stack["ResourceType"] == "Custom::ADConnector":
                                cf_dict["logical_resource_id"] = inner_stack[
                                    "LogicalResourceId"
                                ]
                                cf_dict["logical_resource_id"] = inner_stack[
                                    "ResourceStatus"
                                ]
                                cf_dict["resource_type"] = inner_stack["ResourceType"]
                                cf_resources.append(cf_dict)
                except ClientError as err:
                    if err.response["Error"]["Code"] == "ValidationError":
                        logger.warning(err.response["Error"]["Message"], exc_info=True)
                    else:
                        raise err

        return cf_resources

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise


def extract_provisioned_products(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            sc_client = create_client(
                "servicecatalog", target_role_arn, _region, session
            )
        # iterate over only hub account
        else:
            sc_client = session.client("servicecatalog")

        response = sc_client.search_provisioned_products(
            Filters={
                "SearchQuery": [
                    "productName:SelfServiceResources-SC-PRODUCT-SHARE-AD-CONNECTOR"
                ],
            }
        )

        return [
            {
                "account_id": _account_id,
                "product_name": response["Name"],
                "product_id": response["Id"],
                "status": response["Status"],
            }
            for response in response["ProvisionedProducts"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_instances(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ec2_client = create_client("ec2", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            ec2_client = session.client("ec2")

        paginator = ec2_client.get_paginator("describe_instances")
        response_iterator = paginator.paginate(
            Filters=[
                {
                    "Name": "image-id",
                    "Values": [
                        "ami-01d5152c64e3b1934",
                        "ami-02698288501270d88",
                        "ami-04358a09eecfd5aee",
                        "ami-04e4e2b7ad6f9751c",
                        "ami-05a9650fd78a312ff",
                        "ami-08c59c18ec04dcea7",
                        "ami-090934ddb07e899ac",
                        "ami-0954a605bd82045cd",
                        "ami-0a872190a80515fe8",
                        "ami-0c0c9fb0779efe74d",
                        "ami-0c35c1938e8671db4",
                        "ami-0cfce9f17e0906f08",
                        "ami-0f057dacfea187ce4",
                        "ami-0fef442001a16631d",
                        "ami-003298e702e5665f2",
                        "ami-008264cd2b5a6f128",
                        "ami-023ee612f79500b65",
                        "ami-071c2c2c26d3ac60d",
                        "ami-08698d7b51fb1f365",
                        "ami-088403f080a090b17",
                        "ami-0915d71efed4b5ff6",
                        "ami-0a31d0579ea7d658c",
                        "ami-0afaa73bf7a6d9119",
                        "ami-0b2dbdd1477b97b7b",
                        "ami-0bea00eacf6bb9966",
                        "ami-0deaeeb94f591afbd",
                        "ami-0e9f2ce1283866977",
                        "ami-0ebd79bbf4f33b0ec",
                        "ami-006cfaf43d7a4fca6",
                        "ami-00f758e9db843ca51",
                        "ami-011869136c02aaa9c",
                        "ami-02994ff372c812973",
                        "ami-0693a12ae59b34324",
                        "ami-07c2dad6a4e59a6bf",
                        "ami-0838f0dd6761391ed",
                        "ami-09c219a5d0881cba9",
                        "ami-0a7368b4f3c3b11ae",
                        "ami-0ac1d4887477c5c80",
                        "ami-0bee335885f1017ad",
                        "ami-0d959c2b88d14a544",
                        "ami-0e1986a79f11e5875",
                        "ami-0e71a39fce6672684",
                        "ami-00cb80a73ae8a1eac",
                        "ami-010aabe4901fb63a1",
                        "ami-033e20238c1d50f67",
                        "ami-03b14bf368c2ae5d6",
                        "ami-03e4bb714051e11be",
                        "ami-041e43c9fbaab4811",
                        "ami-0504d590bd810ded3",
                        "ami-0759ab79bf64d5fb3",
                        "ami-07b1b10bdd301555e",
                        "ami-07d64871dae1258c3",
                        "ami-096923669a11c8466",
                        "ami-0ad91b653bc618fa8",
                        "ami-0d86bd02747b7331a",
                        "ami-0ffe2d1eb4c430496",
                        "ami-011e644c3a3610cbf",
                        "ami-020ffe4b3d151d5aa",
                        "ami-04186f7cbb55c2f18",
                        "ami-04a4c518588225088",
                        "ami-04a54f6d99fef08df",
                        "ami-073adb07cba8a41f5",
                        "ami-0ad04c145a0126d3a",
                        "ami-0b4423481f9fcf1bc",
                        "ami-0b50bfd5d03734adc",
                        "ami-0c801a0bac5432622",
                        "ami-0d5f59b1faa12781e",
                        "ami-0dcd0dd42f48787d7",
                        "ami-0df77ed8c02418d1f",
                        "ami-0f1a39826cb0eeabc",
                        "ami-0088b36a1696356a2",
                        "ami-04188fe16de4f9956",
                        "ami-067dc7f8dd1d31e04",
                        "ami-06c0c75902fd5f5e1",
                        "ami-08bdc9428b527541c",
                        "ami-08ca22b64c56f9bc8",
                        "ami-091abadca3add9905",
                        "ami-093abe4552b2c5ac9",
                        "ami-0a1a7a3201ed0e5ce",
                        "ami-0caf9134896732d56",
                        "ami-0cd16978fc05d34f5",
                        "ami-0d38dbb4181f203a9",
                        "ami-0da89ecb330eb41b4",
                        "ami-0ec56244ec30406b7",
                        "ami-015a05b960da42aba",
                        "ami-018482e304bd6e013",
                        "ami-0346c07af1d9c123a",
                        "ami-0447f665bd520a225",
                        "ami-046dc00940d29dc9d",
                        "ami-05f959cc79080bf97",
                        "ami-07bddabf9d8d4ed3e",
                        "ami-088fd85d784b57024",
                        "ami-08fbb97c6f7b3d000",
                        "ami-0918b606583fcee6d",
                        "ami-0a780ac39f9c01ce2",
                        "ami-0b8e4d5c9fa97ce13",
                        "ami-0d7791453334ae27d",
                        "ami-0e4f40894544b7005",
                        "ami-0063e534c406283f6",
                        "ami-00b5dd95164ffbb1e",
                        "ami-046f8fa520e6884c4",
                        "ami-05e692314376192df",
                        "ami-06a5fd22a62f03056",
                        "ami-078c063dbbaa49266",
                        "ami-08345692e4d5c88d3",
                        "ami-08e9186b90c48c579",
                        "ami-0917958b6b8aa4057",
                        "ami-09248bb14959d0fc3",
                        "ami-09a01042840c30735",
                        "ami-0a3a852dfcb96dd94",
                        "ami-0baeedf92afadf3b3",
                        "ami-0f577f7f2cf054678",
                        "ami-0078aee431ad2b013",
                        "ami-01764a357c97a7a92",
                        "ami-0216ae43ed0d374fa",
                        "ami-035ea9b04bee9cebd",
                        "ami-05ac1daa1e4886c02",
                        "ami-05ee54c311fdd71ac",
                        "ami-078f5186e5236159a",
                        "ami-07c4f7c8ae8c1aa74",
                        "ami-07f768651f01da14b",
                        "ami-08d826b0860218541",
                        "ami-093669423334a7be7",
                        "ami-0d84307f54e30ac30",
                        "ami-0ddf83f57af946d55",
                        "ami-0fa987d527a9d9c65",
                        "ami-012fab3e950424d6e",
                        "ami-019f26b470202ca3c",
                        "ami-03ebf1515fb2cc55e",
                        "ami-04a100ae72a472f12",
                        "ami-062035438853ff922",
                        "ami-08381dd87df04740e",
                        "ami-095a25a79c26f9b2d",
                        "ami-0a751f2fc17657b38",
                        "ami-0af1e69b2d65ca319",
                        "ami-0b1a77c2b0c8baed4",
                        "ami-0c10f90aacd5bfc48",
                        "ami-0c8da7c2452289826",
                        "ami-0e453a6878c7a9af9",
                        "ami-0f762d909d7f25e5f",
                        "ami-0193c93cb5b65a0ec",
                        "ami-031aebb2a79c83506",
                        "ami-0382c1132c534c23e",
                        "ami-0483485697201cd2b",
                        "ami-051c61d249181dadf",
                        "ami-07a78d910d2036ff9",
                        "ami-09db35cdf2bb3ed22",
                        "ami-0ab1a33c4b42b9c96",
                        "ami-0d5b92148c902bc16",
                        "ami-0e6d67cfe7cf21b77",
                        "ami-0ee1f9ad854fb7a76",
                        "ami-0fd6adad2f576b0b5",
                        "ami-0fd9cace7a47dc85e",
                        "ami-0ff36dbd106bad747",
                        "ami-007d66b55b6b66b42",
                        "ami-019d6f235111f5555",
                        "ami-01f763bdb925dc3f5",
                        "ami-02f100a97b27cd70c",
                        "ami-0477062f47af40c4a",
                        "ami-04afc90c34cc2ac85",
                        "ami-06b5d289393522fb4",
                        "ami-07368b4fb24070f39",
                        "ami-08d9691ccce2b8365",
                        "ami-0b1d94d83c5bdd18e",
                        "ami-0bd58fff6ae7509f7",
                        "ami-0e3e809dccc83c87c",
                        "ami-0e8b188b6dde2b237",
                        "ami-0e8daea747389d2b7",
                    ],
                },
            ],
        )
        return [
            {
                "account_id": _account_id,
                "instance_id": response["InstanceId"],
                "instance_type": response["InstanceType"],
                "instance_state": response["State"]["Name"],
                "ImageId": response["ImageId"],
                "region": _region,
            }
            for response in response_iterator
            for response in response["Reservations"]
            for response in response["Instances"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_images(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            print(_account_id)
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ec2_client = create_client("ec2", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            ec2_client = session.client("ec2")

        paginator = ec2_client.get_paginator("describe_images")
        response_iterator = paginator.paginate(
            Filters=[
                {
                    "Name": "creation-date",
                    "Values": [
                        # Ireland
                        "2022-12-16T*",
                        "2022-12-2*T*",
                        "2023-01-*T*",
                        "2023-02-*T*",
                        "2023-03-0*T*",
                        "2023-03-10T*",
                        "2023-03-11T*",
                        "2023-03-12T*",
                    ],
                },
                {
                    "Name": "name",
                    "Values": [
                        "*RHEL*",
                        "*SUSE*",
                    ],
                },
            ],
            Owners=[
                _account_id,
            ],
        )
        return [
            {
                "account_id": _account_id,
                "image_id": response["ImageId"],
                "region": _region,
                "name": response["Name"],
            }
            for response in response_iterator
            for response in response["Images"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def tags_per_volume(account_id, ec2_client, item_per_page, key_tag):
    volume_paginator = ec2_client.get_paginator("describe_volumes")
    volume_iterator = volume_paginator.paginate(
        PaginationConfig={"PageSize": item_per_page}
    )
    volumes = []
    for response in volume_iterator:
        for one in response["Volumes"]:
            _tags = []
            for tag in one["Tags"]:
                if key_tag in tag["Key"]:
                    _tags.append(tag["Key"])

            volumes.append(
                {
                    "account_id": account_id,
                    "instance": one["Attachments"][0]["InstanceId"]
                    if len(one["Attachments"]) > 0
                    else "Na",
                    "volume": one["VolumeId"],
                    "state": one["State"],
                    "tags": _tags,
                }
            )

    return volumes


def tags_per_ec2(account_id, ec2_client, item_per_page, key_tag):
    instance_paginator = ec2_client.get_paginator("describe_instances")
    response_iterator = instance_paginator.paginate(
        Filters=[], PaginationConfig={"PageSize": item_per_page}
    )
    instances = []
    for response in response_iterator:
        for one in response["Reservations"]:
            for instance in one["Instances"]:
                _tags = []
                for tag in instance["Tags"]:
                    if key_tag in tag["Key"]:
                        _tags.append(f"{tag['Key']}={tag['Value']}")

                instances.append(
                    {
                        "account_id": account_id,
                        "instance": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "tags": _tags,
                    }
                )

    return instances


def extract_tags(
    _session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    key_tag: str = None,
    item_per_page: int = 50,
    resource_type: str = "EC2",
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ec2_client = create_client("ec2", target_role_arn, _region, _session)
        # iterate over only hub account
        else:
            ec2_client = _session.client("ec2")

        all_tags = []
        if resource_type == "EC2":
            all_tags = tags_per_ec2(_account_id, ec2_client, item_per_page, key_tag)
        elif resource_type == "VOLUME":
            all_tags = tags_per_volume(_account_id, ec2_client, item_per_page, key_tag)
        else:
            raise Exception("provide correct resource type")

        return all_tags

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_ses_verified_identities(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    result = []
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            ses_client = create_client("ses", target_role_arn, _region, session)
        # iterate over only hub account
        else:
            ses_client = session.client("ses")

        paginator = ses_client.get_paginator("list_identities")
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for identity in response["Identities"]:
                result.append(
                    {"identity": identity, "account_id": _account_id, "region": _region}
                )

        return result

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_event_rules(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    prefix: str = "AWS_PLATFORM_",
):
    result = []
    try:
        # Iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            event_client = create_client("events", target_role_arn, _region, session)
        # Iterate over only hub account
        else:
            event_client = session.client("events")

        paginator = event_client.get_paginator("list_rules")
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for rule in response["Rules"]:
                if rule["Name"].startswith(prefix):
                    result.append(
                        {
                            "rule_name": rule["Name"],
                            "account_id": _account_id,
                            "region": _region,
                        }
                    )

        return result

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err


def extract_ssm_documents(
    session: boto3.session.Session,
    _account_id: str = None,
    _region: str = "eu-west-1",
    doc_name: str = "SSM-SessionManagerRunShell",
):
    result = []
    try:
        # Iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            event_client = create_client("ssm", target_role_arn, _region, session)
        # Iterate over only hub account
        else:
            event_client = session.client("ssm")

        paginator = event_client.get_paginator("list_documents")
        response_iterator = paginator.paginate(
            Filters=[
                {"Key": "Owner", "Values": ["Self"]},
            ]
        )

        for response in response_iterator:
            for document in response["DocumentIdentifiers"]:
                if document["Name"].find(doc_name) > -1:
                    result.append(
                        {
                            "account_id": _account_id,
                            "region": _region,
                        }
                    )

        return result

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err
