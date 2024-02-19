import os
import logging
import boto3
from botocore.exceptions import ClientError

LOG_LEVEL = os.getenv("LOG_LEVEL")
SELECTED_ACCOUNTS_STRING = os.getenv("SELECTED_ACCOUNTS")
SELECTED_ACCOUNTS_LIST = SELECTED_ACCOUNTS_STRING.split(",")
CONFIG_RECORDER_EXCLUSION_RESOURCE_STRING = os.getenv(
    "CONFIG_RECORDER_EXCLUDED_RESOURCE_LIST"
)
CONFIG_RECORDER_EXCLUSION_RESOURCE_LIST = (
    CONFIG_RECORDER_EXCLUSION_RESOURCE_STRING.split(",")
)

logging.getLogger().setLevel(LOG_LEVEL)


def lambda_handler(event, context):
    try:
        #  IMPORTANT - Verify boto3 version supports the required configservice api action
        #  Supported version is 1.28.16
        #  Optionally set boto version in requirements.txt for pipeline deployment
        logging.info(f"boto3 version: {boto3.__version__}")

        logging.info(event)
        logging.info(f"Selected Accounts for customization: {SELECTED_ACCOUNTS_LIST}")
        logging.info(
            f"Exclusion Resource List: {CONFIG_RECORDER_EXCLUSION_RESOURCE_LIST}"
        )

        event_source = ""

        if "source" in event:
            event_source = event["source"]
            logging.info(f"Control Tower Event Source: {event_source}")
            event_name = event["detail"]["eventName"]
            logging.info(f"Control Tower Event Name: {event_name}")

        if event_source == "aws.controltower" and event_name == "UpdateManagedAccount":
            account = event["detail"]["serviceEventDetails"][
                "updateManagedAccountStatus"
            ]["account"]["accountId"]
            logging.info(
                f"overriding config recorder for SINGLE account: {account} if in SELECTED accounts"
            )
            override_config_recorder(account, event_name)
        elif event_source == "aws.controltower" and event_name == "UpdateLandingZone":
            logging.info(
                "overriding config recorder for all SELECTED accounts due to UpdateLandingZone event"
            )
            override_config_recorder("", event_name)
        elif event.get("RequestType", "") == "Reset":
            account = event["account"]
            logging.info(
                f"resetting config recorder to the control tower default in account: {account}"
            )
            override_config_recorder(account, event["RequestType"])
        else:
            logging.info("No matching event found")

        logging.info("Execution Successful")

        return

    except Exception as e:
        exception_type = e.__class__.__name__
        exception_message = str(e)
        logging.exception(f"{exception_type}: {exception_message}")
        logging.critical(
            f"Execution failed to complete successfully for event: {event}"
        )


def override_config_recorder(account, event):
    try:
        client = boto3.client("cloudformation")
        paginator = client.get_paginator("list_stack_instances")

        # Create a PageIterator from the Paginator
        if account == "":
            page_iterator = paginator.paginate(
                StackSetName="AWSControlTowerBP-BASELINE-CONFIG"
            )
        else:
            page_iterator = paginator.paginate(
                StackSetName="AWSControlTowerBP-BASELINE-CONFIG",
                StackInstanceAccount=account,
            )

        for page in page_iterator:
            for item in page["Summaries"]:
                account = item["Account"]
                if account in SELECTED_ACCOUNTS_LIST:
                    logging.info(item)
                    region = item["Region"]

                    config_client = create_client(account, region, "config")

                    # Describe existing configuration recorder
                    config_recorder = config_client.describe_configuration_recorders()
                    logging.info(f"Existing Configuration Recorder : {config_recorder}")

                    modify_config_recorder(account, region, config_client, event)

    except Exception as e:
        logging.error(e, exc_info=True)
        raise


def create_client(account_id, region, service, role_name="AWSControlTowerExecution"):
    """
    Return a session in the target account using Control Tower Role
    """
    try:
        sts_client = boto3.client("sts")
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="ConfigCustomizer"
        )
        client = boto3.client(
            service,
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name=region,
        )

        return client
    except ClientError as e:
        logging.error(e, exc_info=True)
        logging.error(f"Unable to assume role in account: {account_id}")
        logging.critical(
            f"Failed to Update Config Recorder for Account: {account_id} and Region: {region}"
        )


def modify_config_recorder(account_id, region, config_client, event):
    """
    Modify Configuration recorder in the target account
    """
    role_arn = (
        "arn:aws:iam::" + account_id + ":role/aws-controltower-ConfigRecorderRole"
    )
    default_role_arn = (
        "arn:aws:iam::"
        + account_id
        + ":role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig"
    )

    try:
        if event == "Reset":
            response = config_client.put_configuration_recorder(
                ConfigurationRecorder={
                    "name": "aws-controltower-BaselineConfigRecorder",
                    "roleARN": default_role_arn,
                    "recordingGroup": {
                        "allSupported": True,
                        "includeGlobalResourceTypes": False,
                    },
                }
            )
            logging.info(f"Response for put_configuration_recorder :{response}")
            config_recorder = config_client.describe_configuration_recorders()
            logging.info(f"Post Change Configuration recorder : {config_recorder}")

        else:
            response = config_client.put_configuration_recorder(
                ConfigurationRecorder={
                    "name": "aws-controltower-BaselineConfigRecorder",
                    "roleARN": role_arn,
                    "recordingGroup": {
                        "allSupported": False,
                        "includeGlobalResourceTypes": False,
                        "exclusionByResourceTypes": {
                            "resourceTypes": CONFIG_RECORDER_EXCLUSION_RESOURCE_LIST
                        },
                        "recordingStrategy": {"useOnly": "EXCLUSION_BY_RESOURCE_TYPES"},
                    },
                }
            )
            logging.info(f"Response for put_configuration_recorder : {response} ")

            config_recorder = config_client.describe_configuration_recorders()
            logging.info(f"Post Change Configuration recorder : {config_recorder}")

    except ClientError as e:
        configrecorder = config_client.describe_configuration_recorders()
        logging.info(f"Exception : {configrecorder}")
        logging.error(e, exc_info=True)
        logging.critical(
            f"Failed to Update Config Recorder for Account: {account_id} and Region: {region}"
        )
