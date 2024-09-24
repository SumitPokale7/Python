#!/usr/bin/env python3
import logging
import boto3
import csv
from botocore.exceptions import ClientError
from argparse import ArgumentParser

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def create_creds(role):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="phz-list")


def create_client(service, role, region):
    """Creates a BOTO3 client using the correct target accounts Role."""
    creds = create_creds(role)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name=region,
    )
    return client


def main(dns_hub_account_id, dns_hub_ireland_vpc_id):
    try:
        role = f"arn:aws:iam::{dns_hub_account_id}:role/AWS_PLATFORM_ADMIN"
        r53_client = create_client("route53", role, 'eu-west-1')
        phz_list = get_phz_list(r53_client, dns_hub_ireland_vpc_id)
        csv_file_path = 'reverse-phzs.csv'
        # Writing to CSV file
        with open(csv_file_path, 'w', newline='') as csv_file:
            fieldnames = ['HostedZoneId', 'Name', 'Owning Account']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            # Write header
            writer.writeheader()
            # Write data
            for phz in phz_list:
                writer.writerow({
                    'HostedZoneId': phz['HostedZoneId'],
                    'Name': phz['Name'],
                    'Owning Account': phz['Owner']['OwningAccount']
                })
    except Exception as e:
        logger.error(e)


def get_phz_list(r53_client, dns_hub_ireland_vpc_id):
    params = {"VPCId": dns_hub_ireland_vpc_id, "VPCRegion": 'eu-west-1'}
    phz_list = []
    while True:
        try:
            response = r53_client.list_hosted_zones_by_vpc(**params)
        except ClientError as e:
            logger.error(f"An error occurred while getting the list of hosted zones associated with the VPC\n Error: {e}")
            raise
        for phz in response['HostedZoneSummaries']:
            if phz['Name'].endswith('.in-addr.arpa.'):
                phz_list.append(phz)
        if not response.get("NextToken"):
            break
        params.update({"NextToken": response["NextToken"]})
    return phz_list


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("dns_hub_account_id", type=str)
    parser.add_argument("dns_hub_ireland_vpc_id", type=str)
    args = parser.parse_args()
    main(args.dns_hub_account_id, args.dns_hub_ireland_vpc_id)
