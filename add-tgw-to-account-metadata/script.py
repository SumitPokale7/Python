#!/usr/bin/env python3
import logging
import boto3
import csv
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set Boto3 Config
BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "standard"})

TGW_REGIONS = [
    "eu-west-1",
    "us-east-1",
    "us-east-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-southeast-3",
    "eu-central-1",
]


class DynamoDB:
    def __init__(self, environment, account_type, processed_accounts) -> None:
        self.account_type = account_type
        self.environment = environment
        self.processed_accounts = processed_accounts
        self.table_name = f"{self.environment}-DYN_METADATA"
        self.ddb_table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
            self.table_name
        )

    def get_accounts_in_scope(self):
        """Grab the active accounts"""
        print("Getting accounts in scope..")
        filter_expression = Attr("status").eq("Active") & Attr("account-type").eq(
            self.account_type
        )

        params = {"FilterExpression": filter_expression}

        result = []
        count = 0
        while True:
            response = self.ddb_table.scan(**params)

            for item in response.get("Items", []):
                if item["account-name"] not in self.processed_accounts:
                    result.append(item)
                    count += 1

            if not response.get("LastEvaluatedKey"):
                break

            params.update(
                {
                    "ExclusiveStartKey": response["LastEvaluatedKey"],
                }
            )
        print(f"Count of accounts to be processed: {count}")
        return result

    def update_account_tgw_attachments_metadata(self, account_name, tgw_metadata):
        """update tgw metadata in account metadata"""
        try:
            self.ddb_table.update_item(
                Key={"account-name": account_name},
                ExpressionAttributeNames={"#FIELD": "tgw-attachments"},
                ExpressionAttributeValues={":value": tgw_metadata},
                UpdateExpression="SET #FIELD = :value",
            )
        except Exception as e:
            logging.error(f"Failed to update {account_name} tgw metadata. Error: {e}")
            raise
        return


class Account:
    def __init__(self, account) -> None:
        self.id = account["account"]
        self.name = account["account-name"]
        self.tgw_attachments = account.get("tgw-attachments", {})
        self.role_arn = f"arn:aws:iam::{self.id}:role/CIP_INSPECTOR"

        self._tgw_metadata = None

    @property
    def tgw_metadata(self):
        if self._tgw_metadata is None:
            self._tgw_metadata = self._format_tgw_attachment_metadata()
        return self._tgw_metadata

    def _create_creds(self, role, region):
        """Assume account role"""
        if region == "ap-southeast-3":  # Jarkata supports only v2 tokens
            sts_client = boto3.client(
                "sts", region, endpoint_url=f"https://sts.{region}.amazonaws.com"
            )
        else:
            sts_client = boto3.client("sts", region)

        return sts_client.assume_role(
            RoleArn=role,
            RoleSessionName="get-account-vpc-tgw-data",
            DurationSeconds=900,
        )

    def _create_account_client(self, service, role, region):
        """Creates a boto3 client using the correct target account role."""
        creds = self._create_creds(role, region)
        account_client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
            config=BOTO3_CONFIG,
        )
        return account_client

    def _get_vpc_cidr(self, vpc_id, region):
        """Get VPC CIDR for the account"""
        ec2_client = self._create_account_client("ec2", self.role_arn, region)
        response = ec2_client.describe_vpcs(
            VpcIds=[
                vpc_id,
            ],
        )["Vpcs"][
            0
        ]["CidrBlock"]
        return response

    def _region_enabled(self, region):
        response = self._create_account_client(
            "ec2", self.role_arn, region="eu-west-1"
        ).describe_regions(RegionNames=[region])["Regions"][0]["OptInStatus"]
        return response

    def _get_account_tgw_attachments(self):
        """Get TGW attachments in all available TGW regions for the account"""
        result = {"tgw_vpc_attachments": []}
        # scan all available TGW regions for tgw attachments
        for region in TGW_REGIONS:
            # Jarkata not enabled in some accounts.
            if (
                region == "ap-southeast-3"
                and self._region_enabled(region) != "opted-in"
            ):
                continue
            ec2_client = self._create_account_client("ec2", self.role_arn, region)
            response = ec2_client.describe_transit_gateway_vpc_attachments(
                Filters=[
                    {
                        "Name": "state",
                        "Values": [
                            "available",
                        ],
                    }
                ],
            )
            # grab all available tgw-attachments per region
            for tgw_vpc_attachment in response["TransitGatewayVpcAttachments"]:
                result["tgw_vpc_attachments"].append(
                    {
                        "region": region,
                        "id": tgw_vpc_attachment["TransitGatewayAttachmentId"],
                        "vpcId": tgw_vpc_attachment["VpcId"],
                    }
                )
        return result

    def _format_tgw_attachment_metadata(self):
        """format for DDB Metadata"""
        tgw_attachments = self._get_account_tgw_attachments()
        result = {}
        for tgw_attachment in tgw_attachments["tgw_vpc_attachments"]:
            cidr = self._get_vpc_cidr(tgw_attachment["vpcId"], tgw_attachment["region"])
            result.update(
                {
                    tgw_attachment["id"]: {
                        "spoke-vpc-cidrs": [cidr],
                        "spoke-vpc-id": tgw_attachment["vpcId"],
                        "spoke-vpc-region": tgw_attachment["region"],
                    }
                }
            )
        return result

    def valid_tgw_metadata(self):
        """Compare and validate current tgw metadata with expected"""
        if len(self.tgw_attachments) != len(self.tgw_metadata):
            return False
        for tgw_attach_id, vpc_details in self.tgw_attachments.items():
            if (
                tgw_attach_id not in self.tgw_metadata
                or self.tgw_metadata[tgw_attach_id] != vpc_details
            ):
                return False
        return True


def main(environment, account_type, filename, processed_accounts):
    ddb = DynamoDB(environment, account_type, processed_accounts)
    accounts_in_scope = ddb.get_accounts_in_scope()

    # output updated accounts to a csv file for reference
    file = open(f"{filename}.csv", "w", newline="")
    out = csv.writer(file, delimiter=",", quoting=csv.QUOTE_ALL)
    out.writerow(["account-name", "account-id", "current", "expected"])

    try:
        count = 0
        for account_metadata in accounts_in_scope:
            account = Account(account_metadata)
            if not account.valid_tgw_metadata():
                ddb.update_account_tgw_attachments_metadata(
                    account.name, account.tgw_metadata
                )
                out.writerow(
                    [
                        account.name,
                        account.id,
                        account.tgw_attachments,
                        account.tgw_metadata,
                    ]
                )
                count += 1
            print(
                f"{account.name} \\"
            )  # print processed accounts to optionally pass in subsequent executions.
        file.close()
    except Exception as e:
        logging.error(e)
        raise
    print(f"DONE.\n{count} accounts updated")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("environment", type=str)
    parser.add_argument("account_type", type=str)
    parser.add_argument(
        "-o", "--output_filename", default="updated-accounts", required=False
    )
    parser.add_argument(
        "-p", "--processed_accounts", default=[], nargs="+", required=False
    )
    args = parser.parse_args()
    main(
        args.environment,
        args.account_type,
        args.output_filename,
        args.processed_accounts,
    )
