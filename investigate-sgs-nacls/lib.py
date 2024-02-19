import boto3
import csv
from boto3.dynamodb.conditions import Attr


def create_creds(role, region):
    sts_client = boto3.client("sts")
    # print(f"Assuming {role} in {region}")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="InvestigateSGNACLSSession"
    )


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


def get_spoke_account_info(hub_account_name, network_type):
    table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
        hub_account_name + "-DYN_METADATA"
    )

    filter_expression = (
        Attr("network-type").eq(network_type)
        & Attr("internet-facing").eq(True)
        & Attr("network-web-only").eq(False)
        & Attr("status").eq("Active")
    )
    params = {"FilterExpression": filter_expression}

    result = []
    count = 0
    while True:
        response = table.scan(**params)
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


class SecurityAudit:
    def __init__(self, spoke_account, spoke_region):
        self.target_role_arn = f"arn:aws:iam::{spoke_account}:role/CIP_INSPECTOR"
        self.region = spoke_region
        self._ec2_client = None

    @property
    def ec2_client(self):
        if self._ec2_client is None:
            self._ec2_client = create_client("ec2", self.target_role_arn, self.region)
        return self._ec2_client

    def _security_group_check(self, account_name, csv_file):
        sgs = self.ec2_client.describe_security_groups()["SecurityGroups"]
        for sg in sgs:
            sg_rules = self.ec2_client.describe_security_group_rules(
                Filters=[{"Name": "group-id", "Values": [sg["GroupId"]]}]
            )["SecurityGroupRules"]
            group_name = sg["GroupName"]
            for sg_rule in sg_rules:
                group_id = sg_rule["GroupId"]
                if sg_rule["IsEgress"] is False:
                    if sg_rule["IpProtocol"] == "-1":
                        ip_protocol = "All"
                        from_port = "All"
                        to_port = "All"
                    elif sg_rule["IpProtocol"] == "50":
                        ip_protocol = "ESP"
                        from_port = "All"
                        to_port = "All"
                    else:
                        ip_protocol = sg_rule["IpProtocol"]
                        from_port = sg_rule["FromPort"]
                        to_port = sg_rule["ToPort"]
                        # If ICMP, report "N/A" for port #
                        if to_port == -1:
                            to_port = "N/A"
                    # Is source/target an IP v4?
                    if "CidrIpv4" in sg_rule:
                        source = sg_rule["CidrIpv4"]
                    # Is source/target an IP v6?
                    elif "CidrIpv6" in sg_rule:
                        source = sg_rule["CidrIpv6"]
                    # Is source/target a security group?
                    elif "ReferencedGroupInfo" in sg_rule:
                        source = sg_rule["ReferencedGroupInfo"]["GroupId"]
                    elif "PrefixListId" in sg_rule:
                        source = sg_rule["PrefixListId"]
                    row = [
                        account_name,
                        group_name,
                        group_id,
                        ip_protocol,
                        source,
                        from_port,
                        to_port,
                    ]
                    write_report(csv_file, row)

    def _nacl_check(self, account_name, csv_file):
        nacls = self.ec2_client.describe_network_acls(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": ["public-subnet-nacl", "firewall-subnet-nacl"],
                }
            ]
        )["NetworkAcls"]
        for nacl in nacls:
            nacl_id = nacl["NetworkAclId"]
            nacl_name = None
            # Check if the NACL has any tags
            if "Tags" in nacl:
                for tag in nacl["Tags"]:
                    if tag["Key"] == "Name":
                        nacl_name = tag["Value"]
                        break
            for entry in nacl["Entries"]:
                if entry["Egress"] is False:
                    direction = "Inbound"
                    rule_action = entry["RuleAction"]
                    rule_number = entry["RuleNumber"]
                    cidr_block = entry.get("CidrBlock", entry.get("Ipv6CidrBlock"))
                    if entry["Protocol"] == "-1":
                        protocol = "All"
                        from_port = "All"
                        to_port = "All"
                    elif entry["Protocol"] == "1":
                        protocol = "ICMP"
                        from_port = "All"
                        to_port = "All"
                    elif entry["Protocol"] == "58":
                        protocol = "IPv6-ICMP"
                        from_port = "All"
                        to_port = "All"
                    else:
                        from_port = entry["PortRange"]["From"]
                        to_port = entry["PortRange"]["To"]
                        # If ICMP, report "N/A" for port #
                        if entry["Protocol"] == "6":
                            protocol = "TCP"
                        elif entry["Protocol"] == "17":
                            protocol = "UDP"
                        else:
                            protocol = entry["Protocol"]

                    row = [
                        account_name,
                        nacl_name,
                        nacl_id,
                        direction,
                        cidr_block,
                        protocol,
                        from_port,
                        to_port,
                        rule_action,
                        rule_number,
                    ]
                    write_report(csv_file, row)
