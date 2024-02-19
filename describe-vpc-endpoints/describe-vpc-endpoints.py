#!/usr/bin/env python3
import logging
import boto3
from argparse import ArgumentParser
import csv

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_creds(role, region):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="firewall-subnets")


def create_client(service, role, region):
    """Creates a BOTO3 client using the correct target accounts Role."""
    creds = create_creds(role, region)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name=region,
    )
    return client


def main(account_type, environment_type):
    try:
        list_accounts = get_connected_spokes(account_type, environment_type)
        # common_subnet_dict = {}
        # common_eni_dict = {}
        for account in list_accounts:
            print("list accounts in main", account)
        print("--------------------------------------------------------------")
        csv = Csv("H2_NonProd.csv")  # add file name here!
        for account in list_accounts:
            account_number = account["account"]["S"]
            role = f"arn:aws:iam::{account_number}:role/CIP_INSPECTOR"
            region = account["region"]["S"]
            # creating client for ec2 to describe VPC endpoints
            client_ec2 = create_client("ec2", role, region)
            response = client_ec2.describe_vpc_endpoints()
            account_list = []
            # csv format printing
            for item in account.values():
                account_list.append(item["S"])
            for VpcEndpoints in response["VpcEndpoints"]:
                csv.set_header(list(account.keys()) + list(VpcEndpoints.keys()))
                csv.append_values(account_list + list(VpcEndpoints.values()))
                print("VpcEndpoints", VpcEndpoints)
        csv.write()

    except Exception as e:
        logging.error(e)


class Csv:
    def __init__(self, filename) -> None:
        self.__header = []
        self.__values = []
        self.filename = filename

    def set_header(self, header):
        self.__header = header

    def append_values(self, values):
        self.__values.append(values)

    def write(self):
        with open(self.filename, "a", newline="") as f:
            w = csv.writer(f, delimiter=",", quoting=csv.QUOTE_ALL)
            w.writerow(self.__header)
            for item in self.__values:
                w.writerow(item)


def get_connected_spokes(account_type, environment_type):
    table_name = "WH-0002-DYN_METADATA"
    params = {
        "TableName": table_name,
        "FilterExpression": "#s = :active AND #at = :accounttype AND #env = :environment",
        "Select": "SPECIFIC_ATTRIBUTES",
        "ProjectionExpression": "#c, account, #at, #accname",
        "ExpressionAttributeNames": {
            "#c": "region",
            "#s": "status",
            "#accname": "account-name",
            "#at": "account-type",
            "#env": "environment-type",
        },
        "ExpressionAttributeValues": {
            ":active": {"S": "Active"},
            ":accounttype": {"S": account_type},
            ":environment": {"S": environment_type},
        },
    }

    result = []
    client = boto3.client("dynamodb", "eu-west-1")
    count = 0
    while True:
        response = client.scan(**params)
        for item in response.get("Items", []):
            result.append(item)
            count = count + 1
        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )
    print(f"Count of accounts to be addressed: {count}")
    return result


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("environment_type", type=str)
    args = parser.parse_args()
    account_type = ["Connected"]

    for network in account_type:
        main(network, args.environment_type)
