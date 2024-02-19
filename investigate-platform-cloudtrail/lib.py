import boto3
import csv
from boto3.dynamodb.conditions import Attr


def create_creds(role):
    sts_client = boto3.client("sts")
    # print(f"Assuming {role} in {region}")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="InvestigateCloudTrail")


def create_client(service, role):
    """Creates a BOTO3 client using the correct target accounts Role."""
    creds = create_creds(role)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name="eu-west-1",
    )
    return client


def get_spoke_account_info(hub_account_name):
    """
    Scan DynamoDB Table to get all spoke accounts in Active status
    :param hub_account_name: Hub name
    :return: result
    """

    metadata_table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
        hub_account_name + "-DYN_METADATA"
    )
    print("Scanning over DDB table: " + metadata_table.table_name)

    filter_expression = Attr("status").eq("Active")
    params = {"FilterExpression": filter_expression}

    result = []

    while True:
        response = metadata_table.scan(**params)

        for item in response.get("Items", []):
            result.append(item)

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )

    return result


def create_report_file(csv_file, columns):
    """
    Creates csv report file with a header
    """
    with open(csv_file, mode="w") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(columns)


def write_report(csv_file, row):
    """
    Writes report data to a csv file
    """
    with open(csv_file, mode="a") as report_file:
        report_writer = csv.writer(
            report_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(row)


class CloudTrial:
    def __init__(self, spoke_account):
        self.target_role_arn = (
            f"arn:aws:iam::{spoke_account}:role/AWSCloudFormationStackSetExecutionRole"
        )
        self._clt_client = None

    @property
    def clt_client(self):
        if self._clt_client is None:
            self._clt_client = create_client("cloudtrail", self.target_role_arn)
        return self._clt_client

    def _cloudtrail_check(self, account_name, account_id, csv_file):
        CloudTrial_Names = self.clt_client.list_trails()["Trails"]
        DS_Cl_Name = "DS_Security_Trail_DO-NOT-MODIFY"
        for cl_name in CloudTrial_Names:
            print(f"the trail name is ${cl_name}")
            if not cl_name["Name"] == DS_Cl_Name:
                CloudTrial_Name = cl_name["Name"]
                Home_Region = cl_name["HomeRegion"]
                row = [account_name, account_id, CloudTrial_Name, Home_Region]
                write_report(csv_file, row)
            else:
                print("Only DS CloudTrail configuration is found")
