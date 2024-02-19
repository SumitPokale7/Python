#!/usr/bin/env python3
import logging
import boto3
import csv
import yaml
from datetime import datetime
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from argparse import ArgumentParser

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "standard"})

# add service and corresponding metadata field name
service_to_metadata_version_field_name = {
    "RBAC": "rbac-version",
    "DNS": "dns_version",
    "DS-AUTOMATION": "ds_automation_version",
}


class DynamoDB:
    def __init__(self, service, environment, processed_accounts) -> None:
        self.service = service
        self.environment = environment
        self.processed_accounts = processed_accounts
        self.table_name = f"{self.environment}-DYN_METADATA"
        self.ddb_table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
            self.table_name
        )

    def get_accounts_in_scope(self):
        print("Getting accounts in scope..")

        # update filters to get the accounts in scope
        filter_expression = (
            Attr("status").eq("Active") & Attr("rbac-ignore-update").exists()
        )

        params = {"FilterExpression": filter_expression}

        result = []
        while True:
            response = self.ddb_table.scan(**params)

            for item in response.get("Items", []):
                if item["account-name"] not in self.processed_accounts:
                    result.append(item)

            if not response.get("LastEvaluatedKey"):
                break

            params.update(
                {
                    "ExclusiveStartKey": response["LastEvaluatedKey"],
                }
            )
        print(f"Total number of accounts to be processed: {len(result)}")
        return result

    def update_account_metadata(self, account_name, service_version):
        try:
            self.ddb_table.update_item(
                Key={"account-name": account_name},
                ExpressionAttributeNames={
                    "#FIELD": service_to_metadata_version_field_name[self.service]
                },
                ExpressionAttributeValues={":value": service_version},
                UpdateExpression="SET #FIELD = :value",
            )
        except Exception as e:
            logging.error(f"Failed to update {account_name} metadata. Error: {e}")
            raise
        return


class Account:
    def __init__(self, account, hs_service) -> None:
        self.id = account["account"]
        self.name = account["account-name"]
        self.region = (
            account["region"] if hs_service in ["DNS"] else "eu-west-1"
        )  # add region based services to list
        self.hs_service = hs_service
        self.metadata_version = account.get(
            service_to_metadata_version_field_name[self.hs_service]
        )
        self.role_arn = f"arn:aws:iam::{self.id}:role/AWSControlTowerExecution"

        self._service_version = None

    @property
    def service_version(self):
        if self._service_version is None:
            self._service_version = self._get_service_version()
        return self._service_version

    def _create_creds(self, role, region="eu-west-1"):
        """Assume account role"""
        sts_client = boto3.client("sts", region)

        return sts_client.assume_role(
            RoleArn=role,
            RoleSessionName="GetServiceVersion",
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

    def _get_service_version(self):
        cfn_client = self._create_account_client(
            "cloudformation", self.role_arn, self.region
        )
        response = cfn_client.get_template(
            StackName=f"{self.name}-CFN-{self.hs_service}-ENGINE"
        )  # update StackName to match the service stack name
        template = response["TemplateBody"]
        parsed_template = yaml.safe_load(template)
        service_version = parsed_template["Metadata"]["Version"]
        return service_version

    def service_version_matches_metadata_version(self):
        """Compare service version to metadata version"""
        return self.service_version == self.metadata_version


def main(hs_service, environment, filename, processed_accounts):
    ddb = DynamoDB(hs_service, environment, processed_accounts)
    accounts_in_scope = ddb.get_accounts_in_scope()

    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d+%H:%M:%S")

    # output updated accounts to a csv file for reference
    file = open(f"{filename}-{formatted_datetime}.csv", "w", newline="")
    out = csv.writer(file, delimiter=",", quoting=csv.QUOTE_ALL)
    out.writerow(
        [
            "account-name",
            "account-id",
            "hs-service",
            "service-version",
            "metadata-version",
        ]
    )

    try:
        count = 0
        for account_metadata in accounts_in_scope:
            account = Account(account_metadata, hs_service)
            if not account.service_version_matches_metadata_version():
                ddb.update_account_metadata(account.name, account.service_version)
                out.writerow(
                    [
                        account.name,
                        account.id,
                        hs_service,
                        account.service_version,
                        account.metadata_version,
                    ]
                )
                count += 1
            print(
                f"{account.name} \\"
            )  # print processed accounts to be skipped in subsequent executions as parameters.
        file.close()
    except Exception as e:
        logging.error(e)
        raise
    print(f"DONE.\n{count} accounts metadata updated")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("environment", type=str)
    parser.add_argument(
        "-o", "--output_filename", default="updated-accounts", required=False
    )
    parser.add_argument(
        "-p", "--processed_accounts", default=[], nargs="+", required=False
    )
    args = parser.parse_args()

    hs_service = "RBAC"  # insert service to process service metadata version mismatch

    main(
        hs_service,
        args.environment,
        args.output_filename,
        args.processed_accounts,
    )
