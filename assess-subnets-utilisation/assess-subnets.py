"""
[I&E] - Capture details from all subnet(s) in particular region
for IaaS account in the AWS Organization.

"""
# Standard packages
import logging
import csv
import os.path
import argparse

# Third party packages
import boto3

# Set logger
LOGGER = logging.getLogger(__name__)
FORMAT = "[%(name)8s()]: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)


def _get_boto3_client(client_type, account_id, region):
    """
    Returns a Boto EC2 Client for a role Arn specified
    :param client_type: String
    :param account_id: String
    :param region: String

    :return: ec2_client object
    """

    ec2_client = boto3.client(client_type, region_name=region)
    return ec2_client


def generate_report_data(ec2_client, account_id, account_name):
    """
    Describes subnets' details in particular AWS account.
    Generates a list of required subnets' information as report_data.
    Returns report_data object.

    :param ec2_client: String
    :param account_id: String
    :param account_name: String

    :return: report_data object
    """
    # Describe all subnets
    subnets = ec2_client.describe_subnets()["Subnets"]
    try:
        if len(subnets) > 0:
            # Create a list of required subnets' information
            LOGGER.info(
                "Creating a list of report data" " for every subnet in the account."
            )
            report_data = []
            for subnet in subnets:
                subnet_id = subnet["SubnetId"]

                # Generate subnet's friendly name
                tags = subnet["Tags"]
                for tag in tags:
                    if tag["Key"] == "Name":
                        subnet_name = f"{tag['Value'][18:-3]}"

                cidr_block = subnet["CidrBlock"]
                available_ips = subnet["AvailableIpAddressCount"]

                # Calculating Total number of IPs supported by subnet's
                # CIDR block and used IPs including (5) AWS reserved ones
                n = int(cidr_block.split("/")[1])
                cidr_ips = 2 ** (32 - n)
                used_ips = cidr_ips - available_ips
                report_data.append(
                    [
                        account_name,
                        subnet_id,
                        subnet_name,
                        cidr_block,
                        available_ips,
                        cidr_ips,
                        used_ips,
                    ]
                )
            return report_data

        else:
            LOGGER.info(
                f"There are no Subnets:{subnets}" f" in the {IAAS_ACCOUNT_ID} account."
            )

    except Exception as e:
        LOGGER.error(e, exc_info=True)


def create_report_file(csv_file):
    """
    Creates CSV report file with a header
    """
    with open(csv_file, mode="w") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(
            [
                "IaaS Account Name",
                "Subnet ID",
                "Subnet Name",
                "Subnet's CIDR block",
                "Available IP Address Count",
                "Total number of IPs supportedby CidrBlock",
                "Used IPs including AWS reserved (5) ones",
            ]
        )
    LOGGER.info("Creating a CSV report file from user input argument...")


def write_report(report_data, csv_file):
    """
    Writes report data to a csv report file
    """
    with open(csv_file, mode="a") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        for row in report_data:
            report_writer.writerow(row)
        LOGGER.info("Inserting report data to the CSV report file...")


def parse_args():
    """Parse required/optional command line arguments."""
    parser = argparse.ArgumentParser()
    parser._action_groups.pop()
    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--account-name",
        required=True,
        help="Please provide the IaaS account name, e.g. WE1-A1",
    )
    required.add_argument(
        "--region",
        required=True,
        help="Please provide the AWS region",
    )

    optional = parser.add_argument_group("Optional arguments")
    optional.add_argument(
        "--output-file",
        help="CSV output file, defaults to filename: subnets-report.csv",
        default="subnets-report.csv",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    """Describes all subnet(s) details in the IaaS account..."""
    args = parse_args()

    STS_CLIENT = boto3.client("sts")
    IAAS_ACCOUNT_ID = boto3.client("sts").get_caller_identity().get("Account")
    IAAS_ACCOUNT_NAME = args.account_name
    LOGGER.info(f"IaaS Account name: {IAAS_ACCOUNT_NAME}")

    # Create CSV report file from user input argument
    CSV_OUTPUT_FILE = args.output_file
    if os.path.exists(CSV_OUTPUT_FILE):
        LOGGER.info("Skipping the CSV report file creation...")
    else:
        create_report_file(CSV_OUTPUT_FILE)

    # Generate report data
    try:
        REGION = args.region
        EC2_CLIENT = _get_boto3_client("ec2", IAAS_ACCOUNT_ID, REGION)
        REPORT_DATA = generate_report_data(
            EC2_CLIENT, IAAS_ACCOUNT_ID, IAAS_ACCOUNT_NAME
        )
        LOGGER.debug("Generated a report data for every subnet in the account.")
    except Exception as exception:
        error_code = str(exception.response.get("Error").get("Code"))
        if error_code == "ExpiredToken":
            raise exception

    # Write generated report data into CSV report file
    try:
        write_report(REPORT_DATA, args.output_file)
    except Exception as error:
        LOGGER.error(error)
        LOGGER.info("Error: There are no subnets to get report data from.")
