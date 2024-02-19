#!/usr/bin/env python3
"""
[I&E] 1905880 - Deletes default VPC for IaaS account(s) in Osaka (ap-northeast-3) region only.

"""
# Standard packages
import logging
import argparse
from pprint import pprint

# Related third party packages
import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ProfileNotFound

# Set logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def delete_vpc_dependencies(ec2_client: str, vpc_id: str, region: str):
    """
    Deletes default VPC dependencies such as IGW and subnets
    :param ec2_client: EC2 low-level service client for IaaS account
    :param vpc_id: Id of the default VPC
    :param region: Region name
    """

    # Describe IGW associated with the vpc
    try:
        resp_desc_igws = ec2_client.describe_internet_gateways(
            Filters=[
                {"Name": "attachment.vpc-id", "Values": [vpc_id]},
            ],
        )["InternetGateways"]
        pprint(resp_desc_igws)
        for item in resp_desc_igws:
            # Detach the IGW
            igw_id = item.get("InternetGatewayId")
            LOGGER.info(
                f"Detaching Internet Gateway ID: {igw_id} from {vpc_id} in {region} region..."
            )
            ec2_client.detach_internet_gateway(
                InternetGatewayId=igw_id, VpcId=vpc_id, DryRun=False
            )

            # Delete the IGW
            LOGGER.info(f"Deleting Internet Gateway ID: {igw_id} in {region} region...")
            ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)
    except Exception as e:
        raise e

    # Describe subnets in VPC
    try:
        resp_desc_subnets = ec2_client.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
            ],
        )["Subnets"]

        # Delete all subnets
        if len(resp_desc_subnets) > 0:
            for item in resp_desc_subnets:
                subnet_id = item.get("SubnetId")
                LOGGER.info(f"Deleting Subnet ID: {subnet_id} in {region} region...")
                ec2_client.delete_subnet(SubnetId=subnet_id, DryRun=False)
    except Exception as e:
        raise e


def iaas_account_expunge_default_vpc(
    ec2_client: str, iaas_account_name: str, region: str
):
    """
    Checks if default VPC is present in spoke account, and deletes its dependencies
    Deletes default VPC itself
    :param ec2_client: EC2 low-level service client for IaaS account
    :param iaas_account_name: IaaS Enterprise account name
    :param region: Region name
    """

    # Describe VPCs
    response = ec2_client.describe_vpcs()
    try:
        if response.get("Vpcs"):
            for vpc in response.get("Vpcs", []):
                vpc_id = vpc.get("VpcId")
                is_default_vpc = True if vpc.get("IsDefault") is True else False
                if is_default_vpc:
                    LOGGER.info(
                        f"Found the default VPC: {vpc_id} in IaaS {iaas_account_name} account"
                    )

                    # Delete dependencies (calling method)
                    LOGGER.info(
                        f"Deleting VPC's: {vpc_id} dependencies for IaaS account: {iaas_account_name} in {region} region..."
                    )
                    delete_vpc_dependencies(ec2_client, vpc_id, region)

                    # Delete VPC
                    LOGGER.info(
                        f"Deleting VPC: {vpc_id} in IaaS account: {iaas_account_name} in {region} region..."
                    )
                    ec2_client.delete_vpc(
                        VpcId=vpc_id,
                    )
                else:
                    LOGGER.info(f"The {vpc_id} is not a default VPC, skipping...")

        else:
            LOGGER.info(
                f"There is no VPC(s) in the IaaS account: {iaas_account_name} in {region} region"
            )

    except Exception as e:
        LOGGER.error(
            {
                "Code": "ERROR DefaultVPCDeletion",
                "Message": "Error deleting default VPC",
            }
        )
        raise e


def parse_args():
    """Parse required/optional command line arguments."""
    parser = argparse.ArgumentParser()
    parser._action_groups.pop()
    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--iaas_account_name",
        required=True,
        help="Please provide the IaaS account name, e.g. WE1-A1",
    )
    required.add_argument(
        "--region",
        required=True,
        help="Please provide the Osaka region name",
        default="ap-northeast-3",
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    osaka_region = args.region
    iaas_account = args.iaas_account_name
    print()
    print("|============|=========================================|")
    ec2_client = boto3.client("ec2", osaka_region)
    iaas_account_expunge_default_vpc(ec2_client, iaas_account, osaka_region)


if __name__ == "__main__":
    try:
        main()

    except ProfileNotFound as err:
        LOGGER.error(err)
        LOGGER.info(
            "Please assume the relevant federated IAM role via AWS Token Broker"
        )

    except ClientError as err:
        error_code = str(err.response.get("Error").get("Code"))
        if error_code == "RequestExpired":
            LOGGER.error(
                {
                    "Code": "ERROR: DELETE DEFAULT VPC",
                    "Message": "An error occurred (RequestExpired) when calling the DescribeVpcs operation: Request has expired",
                }
            )
