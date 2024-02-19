# Standard library imports
import json
import logging
import os
import time

# Third party / External library imports
import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from cfn_tools import load_yaml, dump_yaml

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables
HUB_ACCOUNT_ID = os.environ["HUB_ACCOUNT_ID"]
HUB_ACCOUNT_NAME = os.environ["HUB_ACCOUNT_NAME"]
HUB_TARGET_ROLE = f"arn:aws:iam::{HUB_ACCOUNT_ID}:role/CIP_MANAGER"

sts_client = boto3.client("sts")


def assume_hub_role(role):
    """
    Assume CIP_MANAGER role in the HUB account and return credentials.
    """
    role_session_name = f"{HUB_ACCOUNT_ID}-control-tower-migrator"
    logger.info(f"Assuming {role}")
    return sts_client.assume_role(RoleArn=role, RoleSessionName=role_session_name)[
        "Credentials"
    ]


def assume_spoke_role(account_id):
    """
    Assume CIP_MANAGER role in specified account and return credentials.
    """
    role_arn = f"arn:aws:iam::{account_id}:role/CIP_MANAGER"
    role_session_name = f"{account_id}-control-tower-migrator"
    try:
        sts_response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
    except ClientError as e:
        logger.error(e, exc_info=True)
        raise
    return sts_response


class LambdaTimeout(Exception):
    pass


class Account:
    def __init__(self, account_details) -> None:
        self._creds = None

        self.details = account_details
        self.id = account_details["account"]
        self.name = account_details["account-name"]

        self.iam_client = self._create_client("iam")
        self.config_client = self._create_client("config", "eu-west-1")
        self.ec2_client = self._create_client("ec2", "eu-west-1")

        self.ct_role_name = "AWSControlTowerExecution"
        pass

    @property
    def creds(self):
        if self._creds is None:
            self._creds = self._assume_role()
        return self._creds["Credentials"]

    def _assume_role(self, role_name="CIP_MANAGER"):
        role_arn = f"arn:aws:iam::{self.id}:role/{role_name}"
        role_session_name = f"{self.id}-control-tower-migrator"
        try:
            sts_response = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName=role_session_name
            )
        except ClientError as e:
            logger.error(e, exc_info=True)
            raise
        return sts_response

    def _create_client(self, service, region="us-east-1"):
        """
        Creates a boto3 client service in the specified account.
        """
        client = boto3.client(
            service,
            aws_access_key_id=self.creds["AccessKeyId"],
            aws_secret_access_key=self.creds["SecretAccessKey"],
            aws_session_token=self.creds["SessionToken"],
            region_name=region,
        )
        return client

    def role_exists(self, role_name="AWSControlTowerExecution"):
        """
        Check if Control Tower role exists.
        """
        try:
            self.iam_client.get_role(RoleName=role_name)
            return True
        except ClientError as e:
            logger.debug(e)
            return False

    def create_role(self, role_name, assume_role_policy_document, role_description):
        try:
            self.iam_client.create_role(
                RoleName=role_name,
                Description=role_description,
                MaxSessionDuration=3600,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                Path="/",
            )
        except ClientError as e:
            logger.error(f"Error creating {role_name} role in {self.name}. Error: {e}")
            raise

    def attach_policy_arn_to_role(self, role_name, policy_arn):
        try:
            self.iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        except ClientError as e:
            logger.error(
                f"Error attaching managed policy to {role_name} role in {self.name}. Error: {e}"
            )
            raise

        logger.info(f"Attached policy to {role_name} in {self.name}")
        return

    def get_configuration_recorders(self):
        try:
            output = self.config_client.describe_configuration_recorders()
        except ClientError as e:
            logger.error("Unable to list Config Recorders: %s", str(e))
        recorders = [
            recorder
            for recorder in output["ConfigurationRecorders"]
            if recorder["name"] != "aws-controltower-BaselineConfigRecorder"
        ]
        return recorders

    def get_delivery_channels(self):
        try:
            output = self.config_client.describe_delivery_channels()
        except ClientError as e:
            logger.error("Unable to list Delivery Channels: %s", str(e))
        channels = [
            channel
            for channel in output["DeliveryChannels"]
            if channel["name"] != "aws-controltower-BaselineConfigDeliveryChannel"
        ]
        return channels

    def config_enabled(self):
        if self.get_configuration_recorders() or self.get_delivery_channels():
            logger.debug(f"AWS Config resources found in {self.name}")
            return True
        else:
            logger.info(f"AWS Config resources does not exist in {self.name}")
            return False

    def remove_old_jakarta_config(self):
        jakarta_region = self.ec2_client.describe_regions(
            RegionNames=["ap-southeast-3"], AllRegions=True
        )["Regions"][0]

        if jakarta_region["OptInStatus"] != "opted-in":
            # Jakarta not enabled - can return here
            return

        logger.debug("Jakarta region enabled.")

        jakarta_config_client = self._create_client("config", "ap-southeast-3")

        # Need to delete recorder, delivery channel
        # Delete configuration recorder
        try:
            logger.debug(
                "Deleting DS_Security_Config_Standard configuration recorder in Jakarta"
            )
            jakarta_config_client.delete_configuration_recorder(
                ConfigurationRecorderName="DS_Security_Config_Standard"
            )
        except jakarta_config_client.exceptions.NoSuchConfigurationRecorderException:
            logger.debug("NoSuchConfigurationRecorderException")
            pass

        # Delete delivery channel
        try:
            logger.debug(
                "Deleting DS_Security_Config_Standard delivery channel in Jakarta"
            )
            jakarta_config_client.delete_delivery_channel(
                DeliveryChannelName="DS_Security_Config_Standard"
            )
        except jakarta_config_client.exceptions.NoSuchDeliveryChannelException:
            logger.debug("NoSuchDeliveryChannelException")
            pass


class CloudFormationStack:
    def __init__(self, cfn_client, stack_name) -> None:
        self.name = stack_name
        self.cfn_client = cfn_client
        self.details = self._get_details()
        pass

    def _get_details(self):
        try:
            return self.cfn_client.describe_stacks(StackName=self.name)["Stacks"][0]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ValidationError":
                return None
            raise e

    def exists(self):
        return self.details is not None

    def create(self, template, parameters):
        try:
            response = self.cfn_client.create_stack(
                StackName=self.name,
                TemplateBody=dump_yaml(template),
                DisableRollback=True,
                EnableTerminationProtection=True,
                Parameters=parameters,
            )
            logger.info(f"CFN Create response: {response}")
            return
        except ClientError as e:
            logger.critical(f"Failed to create {self.name} stack. Error: {e.response}")
            raise

    def create_in_progress(self):
        # Refresh stack details
        self.details = self._get_details()
        return self.details["StackStatus"] == "CREATE_IN_PROGRESS"


class ControlTowerMigrator:
    def __init__(self, event):
        self._credentials = None
        self._session = None
        self._metadata_table = None
        self._accounts = event.get("accounts")

        self.ddb_table_name = HUB_ACCOUNT_NAME + "-DYN_METADATA"
        self.region = os.environ["AWS_REGION"]
        self.scan_bool = event.get("scan", False)
        self.ds_sns_topic = event.get(
            "sns_topic",
            "arn:aws:sns:eu-west-1:138543098515:seceng-infra-onboarding-installer-trigger",
        )

        self.sns_client = self._create_client("sns")
        self.sc_client = self._create_client("servicecatalog")
        self.ddb_client = self._create_client("dynamodb")
        self.lambda_client = self._create_client("lambda")
        self.cfn_client = self._create_client("cloudformation")

    @property
    def credentials(self):
        if self._credentials is None:
            self._credentials = assume_hub_role(HUB_TARGET_ROLE)
        return self._credentials

    @property
    def session(self):
        if self._session is None:
            self._session = self._create_session()
        return self._session

    @property
    def metadata_table(self):
        if self._metadata_table is None:
            self._metadata_table = self.session.resource(
                "dynamodb", region_name="eu-west-1"
            ).Table(HUB_ACCOUNT_NAME + "-DYN_METADATA")
        return self._metadata_table

    @property
    def accounts(self):
        if self._accounts is None:
            if self.scan_bool:
                self._accounts = self._get_active_accounts()
            else:
                self._accounts = []
        return self._accounts

    def _create_client(self, service):
        """Creates a BOTO3 client using credentials."""
        return boto3.client(
            service,
            aws_access_key_id=self.credentials["AccessKeyId"],
            aws_secret_access_key=self.credentials["SecretAccessKey"],
            aws_session_token=self.credentials["SessionToken"],
            region_name=self.region,
        )

    def _create_session(self):
        """Creates a BOTO3 session using credentials."""
        return boto3.Session(
            aws_access_key_id=self.credentials["AccessKeyId"],
            aws_secret_access_key=self.credentials["SecretAccessKey"],
            aws_session_token=self.credentials["SessionToken"],
        )

    def _account_metadata(self, account_id):
        response = self.metadata_table.query(
            IndexName='account',
            KeyConditionExpression=Key('account').eq(account_id))
        return response['Items'][0]

    def _get_active_accounts(self):
        """
        Get list of 10 active landing zone accounts in hub environment
        """
        logger.info("Grabbing list of 10 Active LZ Accounts...")
        accounts = []
        filter_expression = (
            Attr("status").eq("Active")
            & Attr("managed-by-control-tower").not_exists()
            & Attr("account-type").ne("Hub")
        )

        params = {"FilterExpression": filter_expression}
        while True:
            response = self.metadata_table.scan(**params)

            for item in response.get("Items", []):
                accounts.append(item)

            if not response.get("LastEvaluatedKey"):
                break

            params.update(
                {
                    "ExclusiveStartKey": response["LastEvaluatedKey"],
                }
            )
        result = accounts[:10]
        return result

    def _self_invoke(self, function_name, payload):
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="Event",
                Payload=json.dumps(payload),
            )
            logger.info(f"Lambda invoke response: {response}")
            return
        except ClientError as e:
            logger.error(f"Error self-invoking lambda. Error: {e}")
            raise

    def deploy_ct_role(self, account):
        """
        Create the required role in an account for migration.
        """
        role_name = "AWSControlTowerExecution"
        if account.role_exists(role_name):
            logger.info(
                f"Control Tower role already exists in {account.name}. Creation skipped."
            )
            return

        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"AWS": [HUB_ACCOUNT_ID]},
            },
        }

        account.create_role(
            role_name=role_name,
            assume_role_policy_document=assume_role_policy_document,
            role_description="Control Tower execution role - customer created",
        )
        account.attach_policy_arn_to_role(
            role_name, "arn:aws:iam::aws:policy/AdministratorAccess"
        )

        logger.info(f"Created Control Tower role in {account.name}")
        return

    def _gen_sns_payloads(self, account) -> list:
        '''
        Create the valid sns payloads.
        One payload to disable services (config) in the managed regions.

        returns a list of payloads to send to DS SNS topic
        '''

        payloads = []

        # Use config delivery channel name in payload
        delivery_channels = account.get_delivery_channels()
        configuration_recorders = account.get_configuration_recorders()
        if len(delivery_channels) > 1:
            raise Exception(
                f"ERROR: Found more than 1 config delivery channel: {delivery_channels}"
            )
        elif len(configuration_recorders) > 1:
            raise Exception(
                f"ERROR: Found more than 1 config recorder: {configuration_recorders}"
            )

        elif len(configuration_recorders) == 1 or len(delivery_channels) == 1:
            config_payload = {"name": "config", "configuration": {}}

            if len(configuration_recorders) == 1:
                config_payload["configuration"][
                    "config_name"
                ] = configuration_recorders[0]["name"]
            if len(delivery_channels) == 1:
                config_payload["configuration"][
                    "config_delivery_channel_name"
                ] = delivery_channels[0]["name"]

            disable_services_payload = {
                'accounts': [
                    {
                        'account_id': account.id,
                        'account_name': account.name,
                        'action': 'disable',
                        'services': [config_payload]
                    }
                ]
            }

            payloads.append(json.dumps(disable_services_payload))

        if payloads:
            logger.info(f"SNS payloads: {payloads}")
        else:
            logger.info("No payload generated")

        return payloads

    def _send_sns_payloads(self, account):
        """
        Send payload to the DS sns topic for offboarding batch of accounts.
        """
        logger.info(f"DS Offboarding action for account {account.name} initiated.")

        logger.info("Sending payloads to DS SNS topic: %s", self.ds_sns_topic)
        for message in self._gen_sns_payloads(account):
            try:
                response = self.sns_client.publish(
                    TopicArn=self.ds_sns_topic, Message=message
                )
                logger.debug(
                    f"Published message with id: {response['MessageId']} to SNS topic SUCCESSFULLY."
                )
            except ClientError as e:
                logger.error("Failed to send SNS payloads: %s", str(e))
                raise

    def _get_sc_provisioned_product_details(self, name):
        try:
            response = self.sc_client.describe_provisioned_product(
                Name=name, AcceptLanguage="en"
            )
            product_status = response["ProvisionedProductDetail"]["Status"]
            if product_status in ["TAINTED", "ERROR"]:
                raise Exception(
                    f"{name} in an unexpected/failed state: {product_status}. "
                    "Resolve errors before re-initiating migration."
                )
            return response["ProvisionedProductDetail"]
        except self.sc_client.exceptions.ResourceNotFoundException:
            logger.info(f"The {name} provisioned product does not exist.")
        except ClientError as e:
            logger.error(
                "An error has been encountered while verifying account status."
            )
            raise e
        return None

    def _terminate_sc_provisioned_product(self, account):
        """
        Delete account product from service catalog landing zone account factory for batch of accounts.
        """
        product_name = f"{account.name}_spoke"
        provisioned_product_details = self._get_sc_provisioned_product_details(
            product_name
        )

        if provisioned_product_details is None:
            return

        if provisioned_product_details["Type"] == "CFN_STACK":  # sanity check
            try:
                self.sc_client.terminate_provisioned_product(
                    ProvisionedProductName=product_name,
                    AcceptLanguage="en",
                    IgnoreErrors=True,
                )
                logger.info(f"Delete request sent for {product_name}")
            except self.sc_client.exceptions.ResourceNotFoundException:
                logger.info(f"The {product_name} provisioned product no longer exist.")
                pass
            except ClientError as e:
                error_message = (
                    "Can't terminate provisioned product because it's still under change "
                    "or its status does not allow further operation"
                )
                if error_message in e.response["Error"]["Message"]:
                    logger.info(
                        f"The {product_name} provisioned product is still under change or being deleted."
                    )
                    pass
                else:
                    logger.error(
                        f"Failed to delete account product from service catalog: {product_name}"
                    )
                    raise e
        else:
            logger.info(
                f"{account.name} SC product is from Control Tower. Termination skipped."
            )

    def _sc_provisioned_product_exists(self, account):
        """
        Verify provisioned products has been terminated successfully.
        """
        logger.debug(
            f"Checking if {account.name} products have been terminated in service catalog..."
        )
        product_name = f"{account.name}_spoke"

        provisioned_product_details = self._get_sc_provisioned_product_details(
            product_name
        )

        logger.debug(f"{product_name} details: {provisioned_product_details}")

        if provisioned_product_details is None:
            return False
        elif provisioned_product_details["Type"] == "CFN_STACK":
            return True
        return False

    def _update_account_ddb_status(self, account):
        """
        Update accounts DDB status to provision to begin provisioning account in control tower
        """

        account_status = self._account_metadata(account.id)["status"]

        if account_status not in ["Provisioning", "CreatingAccount"]:  # sanity check
            try:
                self.ddb_client.update_item(
                    TableName=self.ddb_table_name,
                    Key={"account-name": {"S": account.name}},
                    ExpressionAttributeNames={"#FIELD": "status"},
                    ExpressionAttributeValues={":value": {"S": "Provision"}},
                    UpdateExpression="SET #FIELD = :value",
                )
                logger.info(
                    f"{account.name} status updated to 'Provision' successfully"
                )
                return
            except ClientError as e:
                logger.error(f"Error occurred while updating {account.name} ddb status")
                raise e
        else:
            logger.critical(
                f"{account.name} status Update action ABORTED. Validate the account's current status."
            )

    def _lambda_time_remaining(self, context, seconds=60):
        time_in_milliseconds = seconds * 1000
        if context.get_remaining_time_in_millis() < time_in_milliseconds:
            raise LambdaTimeout(
                f"Lambda has {seconds} seconds remaining before timeout."
            )
        return True

    def _gen_self_invoke_payload(self, accounts):
        payload = {"accounts": accounts, "sns_topic": self.ds_sns_topic}
        return payload

    def _generate_parameters(self, payload):
        """
        Generate parameters for the account resources template
        :param payload: account details
        """
        parameters = []
        template_parameters = [
            "AccountName",
            "AccountId",
            "AccountEmail",
            "AccountType",
            "HubAccountName",
        ]
        parameter_value = {
            "AccountName": payload["accountName"],
            "AccountId": payload["accountId"],
            "AccountEmail": payload["accountEmail"],
            "AccountType": payload["accountType"],
            "HubAccountName": payload["hubAccountName"],
        }

        for parameter_key in template_parameters:
            parameters.append(
                {
                    "ParameterKey": parameter_key,
                    "ParameterValue": parameter_value[parameter_key],
                }
            )
        return parameters

    def create_account_stack(self, account):
        """
        Create Account Resources stack in account
        """
        stack_name = f"{account.name}-CFN-ACCOUNT-RESOURCES"
        account_stack = CloudFormationStack(self.cfn_client, stack_name)

        if not account_stack.exists():
            logger.info(f"Attempting to create {account_stack.name} stack...")

            account_metadata = self._account_metadata(account.id)
            payload = {
                "accountName": account.name,
                "accountId": account.id,
                "accountEmail": account_metadata["root-account"],
                "accountType": account_metadata["account-type"],
                "hubAccountName": HUB_ACCOUNT_NAME,
            }

            template_path = "./templates/account_resources.yaml"
            with open(template_path, "r") as f:
                template = load_yaml(f)

            account_stack.create(template, self._generate_parameters(payload))

        return account_stack

    def migrate_accounts(self, context):
        """
        Migrate accounts to control tower
        """
        remaining_accounts = self.accounts.copy()

        try:
            for account_details in self.accounts:
                # Check lambda has enough time to run
                self._lambda_time_remaining(context)

                account = Account(account_details)
                logger.info(f"Migrating: {account.name} ({account.id})")

                ###############################################################
                # Step 0 - Sanity check if account is already managed by control tower
                if self._account_metadata(account.id).get(
                    "managed-by-control-tower", False
                ):
                    logger.info(
                        f"Skipping: {account.name} ({account.id}). Already managed by control tower"
                    )
                    remaining_accounts.remove(account_details)
                    continue

                ###############################################################
                # Step 1 - create control tower admin role in account
                self.deploy_ct_role(account)

                ###############################################################
                # Step 2 - terminate LDZ SC product for the account
                self._terminate_sc_provisioned_product(account)
                while self._sc_provisioned_product_exists(
                    account
                ) and self._lambda_time_remaining(context):
                    logger.debug(
                        "SC Provisioned product still exists. Waiting and retrying..."
                    )
                    time.sleep(10)

                ###############################################################
                # Step 3 - deploy CT account-resource stack with retains
                account_stack = self.create_account_stack(account)
                # Wait for stack to create
                while (
                    account_stack.create_in_progress()
                    and self._lambda_time_remaining(context)
                ):
                    logger.debug(
                        f"{account_stack.name} is still creating. Waiting and retrying..."
                    )
                    time.sleep(10)
                # Check stack creation was successful
                if account_stack.details["StackStatus"] not in [
                    "CREATE_COMPLETE",
                    "UPDATE_COMPLETE",
                ]:
                    logger.critical(
                        f"INVESTIGATION REQUIRED. {account_stack.name} has failed to complete creation. Status: {account_stack.details['StackStatus']}"
                    )
                    logger.debug(f"Skipping {account.name} {account.id} and continuing")
                    remaining_accounts.remove(account_details)
                    continue

                ###############################################################
                # Step 4 - Remove config configuration from account
                account.remove_old_jakarta_config()
                # Send DS notification to offboard account
                self._send_sns_payloads(account)

                # Wait for offboarding to finish
                while account.config_enabled() and self._lambda_time_remaining(context):
                    logger.debug(
                        f"Config in {account.name} still enabled. Waiting and retrying..."
                    )
                    time.sleep(10)

                ###############################################################
                # Step 5 - update account status to trigger CT build
                self._update_account_ddb_status(account)
                logger.info(f"Migrated: {account.name} ({account.id})")

                remaining_accounts.remove(account_details)

        except LambdaTimeout as e:
            logger.info(e)
            self._self_invoke(
                context.function_name, self._gen_self_invoke_payload(remaining_accounts)
            )
        except Exception as e:
            logger.critical(e, exc_info=True)
            raise e
        finally:
            logger.info(
                f"Remaining payload: {self._gen_self_invoke_payload(remaining_accounts)}"
            )

        logger.info("Finished processing all accounts.")


def lambda_handler(event, _context):
    logger.info(event)

    control_tower_migrator = ControlTowerMigrator(event)

    logger.info("Begin migration")

    control_tower_migrator.migrate_accounts(_context)
