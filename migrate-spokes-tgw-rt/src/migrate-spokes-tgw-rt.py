# Standard library imports
import os
import logging
import time

# Third party / External library imports
import boto3
import json
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# Set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables
HUB_ACCOUNT_ID = os.environ["HUB_ACCOUNT_ID"]
HUB_ACCOUNT_NAME = os.environ["HUB_ACCOUNT_NAME"]
HUB_TARGET_ROLE = f"arn:aws:iam::{HUB_ACCOUNT_ID}:role/CIP_MANAGER"


region_to_shorthand = {
    "eu-west-1": "WE1",
    "us-east-2": "WU2",
    "ap-southeast-2": "WAP2",
    "ap-southeast-1": "WAP1",
}


def create_credentials(role):
    sts_client = boto3.client("sts")
    logger.info(f"Assuming {role}")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="TgwMigrator")[
        "Credentials"
    ]


class TgwRtMigrator:
    def __init__(self, event):
        self._credentials = None
        self._ec2_client = None
        self._lambda_client = None
        self._session = None
        self._target_tgw_rt_id = None
        self._other_tgw_rt_id = None
        self._tgw_rts = None
        self._tgw_attachments = None
        self._metadata_table = None
        self._account_attachment_dict = None
        self.scan_bool = event.get("scan", False)
        self._accounts = event.get("accounts")

        self.region = event.get("region", os.environ["AWS_REGION"])
        self.action = event.get("action")
        self.tgw_rt_name = event.get("tgw_rt_name")
        self.tgw_rt_name_other = event.get("tgw_rt_name_other")
        self.delete_static_route = event.get("delete_static_route", False)
        self.no_dynamodb = event.get("no_dynamodb", False)

    @property
    def credentials(self):
        if self._credentials is None:
            self._credentials = create_credentials(HUB_TARGET_ROLE)
        return self._credentials

    @property
    def ec2_client(self):
        if self._ec2_client is None:
            self._ec2_client = self._create_client("ec2")
        return self._ec2_client

    @property
    def lambda_client(self):
        if self._lambda_client is None:
            self._lambda_client = self._create_client("lambda")
        return self._lambda_client

    @property
    def session(self):
        if self._session is None:
            self._session = self._create_session()
        return self._session

    @property
    def accounts(self):
        if self._accounts is None:
            if self.scan_bool:
                self._accounts = self._get_account_ids()
            else:
                self._accounts = []
        return self._accounts

    @property
    def metadata_table(self):
        if self._metadata_table is None:
            self._metadata_table = self.session.resource(
                "dynamodb", region_name="eu-west-1"
            ).Table(HUB_ACCOUNT_NAME + "-DYN_METADATA")
        return self._metadata_table

    @property
    def target_tgw_rt_id(self):
        if self._target_tgw_rt_id is None:
            if self.action == "revert":  # Revert back to onprem
                self._target_tgw_rt_id = self._get_tgw_rt_id(
                    f"{HUB_ACCOUNT_NAME}-{region_to_shorthand[self.region]}-TGW-01-RT-OnPrem-01"
                )
            elif self.action == "migrate":  # Migrate to the tgw rt that passed by user
                self._target_tgw_rt_id = self._get_tgw_rt_id(
                    f"{HUB_ACCOUNT_NAME}-{region_to_shorthand[self.region]}-{self.tgw_rt_name}"
                )
            if self.delete_static_route is True:
                self._other_tgw_rt_id = self._get_tgw_rt_id(
                    f"{HUB_ACCOUNT_NAME}-{region_to_shorthand[self.region]}-{self.tgw_rt_name_other}"
                )
        return self._target_tgw_rt_id, self._other_tgw_rt_id

    @property
    def tgw_rts(self):
        if self._tgw_rts is None:
            self._tgw_rts = self.ec2_client.describe_transit_gateway_route_tables()[
                "TransitGatewayRouteTables"
            ]
        return self._tgw_rts

    @property
    def tgw_attachments(self):
        if self._tgw_attachments is None:
            params = {
                "Filters": [{"Name": "resource-type", "Values": ["vpc"]}],
            }
            result = []

        while True:
            response = self.ec2_client.describe_transit_gateway_attachments(**params)
            for attachment in response.get("TransitGatewayAttachments", []):
                result.append(attachment)
            if response.get("NextToken", None) is None:
                break
            params.update(
                {
                    "NextToken": response.get("NextToken"),
                }
            )

        self._tgw_attachments = result

        return self._tgw_attachments

    @property
    def account_attachment_dict(self):
        if self._account_attachment_dict is None:
            self._account_attachment_dict = {}
            for attachment in self.tgw_attachments:
                attachment_object = {
                    "TransitGatewayAttachmentId": attachment[
                        "TransitGatewayAttachmentId"
                    ],
                    "TransitGatewayRouteTableId": attachment.get("Association", {}).get(
                        "TransitGatewayRouteTableId"
                    ),
                }

                if self._account_attachment_dict.get(attachment["ResourceOwnerId"]):
                    self._account_attachment_dict[attachment["ResourceOwnerId"]].append(
                        attachment_object
                    )
                else:
                    self._account_attachment_dict[attachment["ResourceOwnerId"]] = [
                        attachment_object
                    ]

        return self._account_attachment_dict

    def _get_tgw_rt_id(self, rt_name):
        logger.info(f"Finding TGW ID with name: {rt_name}")
        for tgw_rt in self.tgw_rts:
            for tag in tgw_rt["Tags"]:
                if tag["Key"] == "Name" and tag["Value"] == rt_name:
                    return tgw_rt["TransitGatewayRouteTableId"]
        logger.warning(f"Did not find any TGW ID with name: {rt_name}")
        return None

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

    def _get_account_ids(self):
        logger.info("Scanning over DDB table: " + self.metadata_table.table_name)

        filter_expression = (
            Attr("status").eq("Active")
            & Attr("account-type").eq("Connected")
            & Attr("region").eq(self.region)
        )

        params = {"FilterExpression": filter_expression}
        result = []

        while True:
            response = self.metadata_table.scan(**params)

            for item in response.get("Items", []):
                result.append(item)

            if not response.get("LastEvaluatedKey"):
                break

            params.update(
                {
                    "ExclusiveStartKey": response["LastEvaluatedKey"],
                }
            )

        return [account["account"] for account in result]

    def _self_invoke(self, function_name, remaining_accounts_payload):
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="Event",
                Payload=json.dumps(remaining_accounts_payload),
            )
            logger.info(f"Lambda invoke response: {response}")
            return
        except ClientError as e:
            logger.info(f"remaining account: {remaining_accounts_payload['accounts']}")
            logger.error("Error self-invoking lambda")
            raise e

    def _get_account_tgw_attachment_details(self, account):
        attachment_list = []
        for attachment in self.tgw_attachments:
            if attachment["ResourceOwnerId"] == account:
                attachment_list.append(attachment)
        return attachment

    def _disassociation_waiter(self, attachment_id):
        for counter in range(12):
            attachment_status = self.ec2_client.describe_transit_gateway_attachments(
                TransitGatewayAttachmentIds=[attachment_id]
            )["TransitGatewayAttachments"][0]

            if attachment_status.get("Association"):
                logger.info(f"Counter: {counter}. Waiting 5 secs for disassociation")
                time.sleep(5)
            else:
                return

    def _get_account_cidr(self, account):
        cidr_value = []
        account_details = {}
        self._metadata_table = self.session.resource(
            "dynamodb", region_name="eu-west-1"
        ).Table(HUB_ACCOUNT_NAME + "-DYN_METADATA")
        try:
            response = self._metadata_table.query(
                IndexName="account",
                Limit=1,
                KeyConditionExpression="account = :id",
                ExpressionAttributeValues={":id": account},
            )
            if not response.get("Items"):
                logger.error(f"Spoke '{account}' does not exist")
                raise RuntimeError(f"no metadata found for {account} account")
        except Exception as e:
            logger.critical(
                {
                    "Code": "ERROR Lambda SelfServiceResources Service",
                    "Message": f"Error getting '{account}' details from DDB metadata table",
                }
            )
            raise e

        if response.get("Items"):
            account_details = response["Items"][0]
            cidr_value.append(account_details.get("ip-range"))
            return cidr_value

    def _migrate_account(self, account):
        if self.delete_static_route is True:
            connected_account_cidr = self._get_account_cidr(account)
            logger.info(connected_account_cidr)

        for attachment in self.account_attachment_dict.get(account):
            if attachment["TransitGatewayRouteTableId"] == self._target_tgw_rt_id:
                logger.info(
                    f"Account: {account}. Attachment: {attachment['TransitGatewayAttachmentId']} already associated to table: {attachment['TransitGatewayRouteTableId']}"
                )
                continue

            if attachment["TransitGatewayRouteTableId"]:
                logger.info(
                    f"Account: {account}. Disassociating attachment: {attachment['TransitGatewayAttachmentId']} from table: {attachment['TransitGatewayRouteTableId']}"
                )
                self.ec2_client.disassociate_transit_gateway_route_table(**attachment)
                if self.delete_static_route:
                    if self.action == "revert":
                        logger.info(
                            f"Account: {account}. Adding Static Route: {connected_account_cidr[0]} to table: {self._other_tgw_rt_id}"
                        )
                        self.ec2_client.create_transit_gateway_route(
                            DestinationCidrBlock=connected_account_cidr[0],
                            TransitGatewayRouteTableId=self._other_tgw_rt_id,
                            TransitGatewayAttachmentId=attachment[
                                "TransitGatewayAttachmentId"
                            ],
                            DryRun=False,
                        )
                    elif self.action == "migrate":
                        logger.info(
                            f"Account: {account}. Deleting Static Route: {connected_account_cidr[0]} from table: {self._other_tgw_rt_id}"
                        )
                        self.ec2_client.delete_transit_gateway_route(
                            TransitGatewayRouteTableId=self._other_tgw_rt_id,
                            DestinationCidrBlock=connected_account_cidr[0],
                            DryRun=False,
                        )
            logger.info(
                f"Account: {account}. Associating attachment: {attachment['TransitGatewayAttachmentId']} with table: {self.target_tgw_rt_id[0]}"
            )
            max_counter = 90
            for counter in range(max_counter):
                try:
                    self.ec2_client.associate_transit_gateway_route_table(
                        TransitGatewayRouteTableId=self.target_tgw_rt_id[0],
                        TransitGatewayAttachmentId=attachment[
                            "TransitGatewayAttachmentId"
                        ],
                    )
                    logger.info(
                        f"Account: {account}. Successfully associated attachment: {attachment['TransitGatewayAttachmentId']} with table: {self.target_tgw_rt_id[0]}"
                    )
                    return
                except ClientError as e:
                    if (
                        e.response["Error"]["Code"] == "Resource.AlreadyAssociated"
                        and counter < max_counter - 1
                    ):
                        logger.debug(
                            f"Counter: {counter}. Waiting 1 second for disassociation"
                        )
                        time.sleep(1)
                    else:
                        raise e

    def _migrate_unmanaged_account(self, account):
        if account["TGWRoutetableID"] != self._target_tgw_rt_id:
            logger.info(
                f"Account: {account['account-id']}. Attachment: {account['TGWAttachmentID']} is not associated to table: {self._target_tgw_rt_id}"
            )
            logger.info(
                f"Account: {account}. Disassociating attachment: {account['TGWAttachmentID']} from table: {account['TGWRoutetableID']}"
            )
            self.ec2_client.disassociate_transit_gateway_route_table(
                TransitGatewayRouteTableId=account["TGWRoutetableID"],
                TransitGatewayAttachmentId=account["TGWAttachmentID"],
            )

            if self.delete_static_route:
                if self.action == "revert":
                    logger.info(
                        f"Account: {account['account-id']}. Adding Static Route: {account['VPCCIDRID']} to table: {self._other_tgw_rt_id}"
                    )
                    self.ec2_client.create_transit_gateway_route(
                        DestinationCidrBlock=account["VPCCIDRID"],
                        TransitGatewayRouteTableId=self._other_tgw_rt_id,
                        TransitGatewayAttachmentId=account["TGWAttachmentID"],
                        DryRun=False,
                    )
                elif self.action == "migrate":
                    logger.info(
                        f"Account: {account['account-id']}. Deleting Static Route: {account['VPCCIDRID']} from table: {self._other_tgw_rt_id}"
                    )
                    self.ec2_client.delete_transit_gateway_route(
                        TransitGatewayRouteTableId=self._other_tgw_rt_id,
                        DestinationCidrBlock=account["VPCCIDRID"],
                        DryRun=False,
                    )
            max_counter = 90
            logger.info(
                f"Account: {account['account-id']}. Associating attachment: {account['TGWAttachmentID']} with table: {self.target_tgw_rt_id[0]}"
            )
            for counter in range(max_counter):
                try:
                    self.ec2_client.associate_transit_gateway_route_table(
                        TransitGatewayRouteTableId=self.target_tgw_rt_id[0],
                        TransitGatewayAttachmentId=account["TGWAttachmentID"],
                    )
                    logger.info(
                        f"Account: {account}. Successfully associated attachment: {account['TGWAttachmentID']} with table: {self.target_tgw_rt_id[0]}"
                    )
                    return
                except ClientError as e:
                    if (
                        e.response["Error"]["Code"] == "Resource.AlreadyAssociated"
                        and counter < max_counter - 1
                    ):
                        logger.debug(
                            f"Counter: {counter}. Waiting 1 second for disassociation"
                        )
                        time.sleep(5)
                    else:
                        raise e
        else:
            logger.info(
                f"Account: {account['account-id']}. Attachment: {account['TGWAttachmentID']} is already associated to table: {account['TGWRoutetableID']}"
            )

    def migrate_accounts(self, context=None):
        if self.action not in ["migrate", "revert"]:
            logger.warning(
                "Event action is not 'migrate' or 'revert'. Taking no action..."
            )
            return

        logger.info(f"Accounts to action: {len(self.accounts)}")
        remaining_accounts_payload = {
            "accounts": self.accounts.copy(),
            "region": self.region,
            "action": self.action,
            "delete_static_route": self.delete_static_route,
            "tgw_rt_name": self.tgw_rt_name,
            "tgw_rt_name_other": self.tgw_rt_name_other,
            "no_dynamodb": self.no_dynamodb,
        }

        logger.info(f"Target TGW RT ID: {self.target_tgw_rt_id}")

        if remaining_accounts_payload["no_dynamodb"] is False:
            for account in self.accounts:
                if (
                    context and context.get_remaining_time_in_millis() < 120000
                ):  # 120 seconds before timeout
                    self._self_invoke(context.function_name, remaining_accounts_payload)
                    logger.info(
                        f"remaining account: {remaining_accounts_payload['accounts']}"
                    )
                    return

                try:
                    self._migrate_account(account)
                except Exception as e:
                    logger.info(
                        f"remaining account: {remaining_accounts_payload['accounts']}"
                    )
                    raise e

                remaining_accounts_payload["accounts"].remove(account)
        else:
            for account in self.accounts:
                try:
                    self._migrate_unmanaged_account(account)
                except Exception as e:
                    logger.info(f"Unmanaged DynamoDB Accounts: {account['account-id']}")
                    raise e


def lambda_handler(event, _context):
    logger.info(event)

    tgw_rt_migrator = TgwRtMigrator(event)

    logger.info(f"Action: {tgw_rt_migrator.action}. Region: {tgw_rt_migrator.region}")

    tgw_rt_migrator.migrate_accounts(_context)
