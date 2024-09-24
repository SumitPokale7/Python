import boto3
import time
import os
import concurrent.futures
from operator import itemgetter
import datetime
from typing import Final
import csv
import logging
import sys

# Read the variables from the CSV file
csv_file_path = "account_details.csv"


input_account_name: Final = os.getenv("Account_Name", "WS-Y0T0")
instance_count: Final = int(os.getenv("Instance_Count", 10))
DryRun: Final = os.getenv("Dry_Run", "False")
Boostrapping_Flag: Final = 0

with open(csv_file_path, mode="r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if row["ACCOUNT_NAME"] == input_account_name:
            ACCOUNT_NAME = row["ACCOUNT_NAME"]
            ACCOUNT_ID = row["ACCOUNT_ID"]
            REGION = row["REGION"]
            SECURITY_GROUP_ID = row["SECURITY_GROUP_ID"]
            SUBNET_IDS = row["SUBNET_ID"].split(";")

            INSTANCE_PROFILE = f"{ACCOUNT_NAME}-role_INSTANCE"
            basedir = os.path.abspath(os.path.dirname(__file__))
            _UserData = os.path.join(basedir, "EC2LinuxUserData.sh")
        basedir = os.path.abspath(os.path.dirname(__file__))
        _UserData = os.path.join(basedir, "EC2LinuxUserData.sh")

        logger = logging.getLogger(__name__)

        def get_client_by_service(region, account_id, account_name, service_name):
            credentials = get_target_account_sts_credentials(account_name, account_id)
            try:
                client = boto3.client(
                    service_name,
                    aws_access_key_id=credentials.get("AccessKeyId"),
                    aws_secret_access_key=credentials.get("SecretAccessKey"),
                    aws_session_token=credentials.get("SessionToken"),
                    region_name=region,
                )
                return client
            except Exception as e:
                print("An error occurred:", str(e))
                return None

        def get_target_account_sts_credentials(account_name, account_id):
            """
            Function to get credentials for target account
            :param account_name:
            :param account_id:
            :return credentials:
            """
            target_role_arn = f"arn:aws:iam::{account_id}:role/AWS_PLATFORM_ADMIN"
            sts_client = boto3.client("sts")
            logger.info(f"Assuming target role in account {account_name}")
            credentials = sts_client.assume_role(
                RoleArn=target_role_arn, RoleSessionName="DomainJoin"
            )["Credentials"]
            logger.info(f"Target role in account {account_name} has been assumed")

            return credentials

        def create_or_get_security_group(ec2_client, subnet_id):
            response = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": ["automation-test-sg"]}]
            )

            if response["SecurityGroups"]:
                sg_id = response["SecurityGroups"][0]["GroupId"]
                return sg_id
            try:
                response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
                if "Subnets" in response and response["Subnets"]:
                    vpc_id = response["Subnets"][0]["VpcId"]
                else:
                    return None

                security_group = ec2_client.create_security_group(
                    GroupName="automation-test-sg",
                    Description="Automation test security group",
                    VpcId=vpc_id,
                )
                sg_id = security_group["GroupId"]
                ec2_client.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                    ],
                )
                ec2_client.authorize_security_group_egress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                    ],
                )
                return sg_id
            except Exception as e:
                print("An error occurred:", str(e))
                return None

        def calculate_elapsed_time(start_time):
            end_time = datetime.datetime.now()
            elapsed_time_seconds = (end_time - start_time).total_seconds()
            elapsed_time_minutes = elapsed_time_seconds / 60
            elapsed_time_minutes_rounded = round(elapsed_time_minutes, 2)
            return elapsed_time_minutes_rounded

        def get_private_subnet_id(ec2_client):
            response = ec2_client.describe_subnets(
                Filters=[{"Name": "tag:Name", "Values": ["private-*"]}]
            )
            private_subnet_id = response["Subnets"][0]["SubnetId"]
            return private_subnet_id

        def get_latest_image(ec2_client, ami_name, architecture="x86_64"):
            response = ec2_client.describe_images(
                Filters=[
                    {
                        "Name": "name",
                        "Values": [ami_name + "*"],
                    },
                    {
                        "Name": "architecture",
                        "Values": [architecture],
                    },
                    {
                        "Name": "virtualization-type",
                        "Values": [
                            "hvm"
                        ],  # Adjust the value based on the virtualization type you want (hvm or paravirtual)
                    },
                ],
            )
            # Sort on Creation date Desc
            image_details = sorted(
                response["Images"], key=itemgetter("CreationDate"), reverse=True
            )
            ami_id = image_details[0]["ImageId"]
            return ami_id

        def wait_for_instance_status(ec2_client, instance_id, region="eu-west-1"):
            # ec2_client = boto3.client('ec2', region_name=region)
            print(f"Waiting for instance {instance_id} to pass 2/2 status checks...")
            waiter = ec2_client.get_waiter("instance_status_ok")
            waiter.wait(
                InstanceIds=[instance_id], WaiterConfig={"Delay": 15, "MaxAttempts": 40}
            )
            print(f"Instance {instance_id} has passed 2/2 status checks.")

        def print_colored(message, color_code):
            print(f"\033[{color_code}m{message}\033[0m")

        def getUserData():
            with open(_UserData, "r") as f:
                return f.read()

        def wait_for_bootstrappingtag(
            ec2_client, instance_id, tag_key, max_attempts, sleep_seconds
        ):
            attempts = 0
            while attempts < max_attempts:
                try:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    tags = response["Reservations"][0]["Instances"][0].get("Tags", [])
                    for tag in tags:
                        if tag["Key"] == tag_key:
                            if tag["Value"] == "bootstrapping":
                                print_colored(
                                    f"Instance {instance_id} bootstrapping successful!",
                                    33,
                                )  # 33 is the ANSI color code for yellow
                                return "bootstrapping"
                            else:
                                return tag["Value"]
                        else:
                            attempts += 1
                            time.sleep(sleep_seconds)

                except Exception as e:
                    print(f"Error describing instance tags: {e}")
            print(
                f"Timeout: Tag {tag_key} not applied to instance {instance_id} after {max_attempts} attempts"
            )

        def wait_for_tag(ec2_client, instance_id, tag_key, max_attempts, sleep_seconds):
            attempts = 0
            while attempts < max_attempts:
                try:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    tags = response["Reservations"][0]["Instances"][0].get("Tags", [])
                    for tag in tags:
                        if tag["Key"] == tag_key:
                            if tag["Value"] == "bootstrapped":
                                print_colored(
                                    f"Instance {instance_id} bootstrap successful!", 32
                                )  # 32 is the ANSI color code for green
                                return "bootstrapped"
                            elif tag["Value"] == "bootstrap-skipped":
                                print_colored(
                                    f"Instance {instance_id} bootstrap skipped!", 30
                                )  # 30 is the ANSI color code for grey
                                return "bootstrap-skipped"
                            elif tag["Value"] == "bootstrap-failed":
                                print_colored(
                                    f"Instance {instance_id} bootstrap failed!", 31
                                )  # 31 is the ANSI color code for red
                                return "bootstrap-failed"
                except Exception as e:
                    print(f"Error describing instance tags: {e}")
                attempts += 1
                time.sleep(sleep_seconds)
            print(
                f"Timeout: Tag {tag_key} not applied to instance {instance_id} after {max_attempts} attempts"
            )

        def create_instance(
            ec2_client, os_type, tags, instance_count, subnet_id, dry_run=False
        ):
            if "WINDOWS22" in os_type:
                ami_name = "Windows_Server-2022-English-Full-Base"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "2022"
                # document_arn = 'arn:aws:ssm:eu-west-1:{{ACCOUNT_NAME}}:document/BpPlatformServices_WIN_DomainJoin'
            elif "WINDOWS19" in os_type:
                ami_name = "Windows_Server-2019-English-Full-Base-2024.02.14"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "WINDOWS19"
            elif "WINDOWS16" in os_type:
                ami_name = "Windows_Server-2016-English-Full-Base-2024.02.14"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "WINDOWS16"
            elif "RHEL920" in os_type:
                ami_name = "RHEL-9.2.0_HVM-20240521-x86_64-93-Hourly2-GP3"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "9.2.0"
            elif "RHEL810" in os_type:
                ami_name = "RHEL-8.10.0_HVM-20240514-x86_64-76-Hourly2-GP3"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "8.1.0"
            elif "RHEL8ARM" in os_type:
                ami_name = "RHEL-8.9.0_HVM-20240213-arm64-3-Hourly2-GP3"
                ami_id = get_latest_image(ec2_client, ami_name, "arm64")
                os_version = "8.9.A"
            elif "RHEL790" in os_type:
                ami_name = "RHEL-7.9_HVM-20221027-x86_64-0-Hourly2-GP2"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "7.9.0"
                # document_arn = 'arn:aws:ssm:eu-west-1:{{ACCOUNT_NAME}}:document/BpPlatformServices_RHEL_DomainJoin'
            elif "RHEL940" in os_type:
                ami_name = "RHEL-9.4.0_HVM-20240605-x86_64-82-Hourly2-GP3"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "9.4.0"
            elif "SUSE15" in os_type:
                ami_name = "suse-sles-15-sp5-v20240129-hvm-ssd-x86_64"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "15 SP5"
                # document_arn = 'arn:aws:ssm:eu-west-1:{{ACCOUNT_NAME}}:document/BpPlatformServices_SLES_DomainJoin'
            elif "SUSE12" in os_type:
                ami_name = "suse-sles-12-sp5-v20240308-hvm-ssd-x86_64"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "12 SP5"
                # document_arn = 'arn:aws:ssm:eu-west-1:{{ACCOUNT_NAME}}:document/BpPlatformServices_SLES_DomainJoin'
            elif "UBUNTU" in os_type:
                ami_name = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64"
                ami_id = get_latest_image(ec2_client, ami_name)
                os_version = "22.04"
                # document_arn = 'arn:aws:ssm:eu-west-1:{{ACCOUNT_NAME}}:document/BpPlatformServices_Ubuntu_DomainJoin'
            else:
                ami_id = "ami-08e592fbb0f535224"  # Default AMI ID for RHEL
                os_version = "9.3.0"

            # Set the instance details
            SECURITY_GROUP_ID = create_or_get_security_group(ec2_client, subnet_id)
            bootstrapping_run_time = ""

            instance_details = {
                "ImageId": ami_id,
                "InstanceType": "t3.large" if "RHEL8ARM" not in os_type else "t4g.large",
                "Monitoring": {"Enabled": False},
                "SecurityGroupIds": [SECURITY_GROUP_ID],
                "SubnetId": subnet_id,
                "UserData": getUserData(),
                "IamInstanceProfile": {"Name": INSTANCE_PROFILE},
                "BlockDeviceMappings": [
                            {
                                'DeviceName': '/dev/sda1',
                                'Ebs': {
                                    'VolumeSize': 30,
                                    'VolumeType': 'gp3',
                                    'DeleteOnTermination': True
                                }
                            }
                        ],
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": tags,
                    }
                ],
                "MinCount": instance_count,
                "MaxCount": instance_count,
            }

            # Record start time
            start_time = datetime.datetime.now()
            print(f"Time keeping started at {start_time} in {ACCOUNT_NAME} / {REGION}")
            instances = []
            # Create the instance
            # Perform the dry run
            if dry_run:
                try:
                    ec2_client.run_instances(**instance_details, DryRun=True)
                    print("Dry run successful. No instances were created.")
                    sys.exit(1)
                except ec2_client.exceptions.ClientError as e:
                    if "DryRunOperation" in str(e):
                        print("Dry run successful. No instances were created.")
                    else:
                        print(f"Error during dry run: {e}")
            else:
                try:
                    instances = ec2_client.run_instances(**instance_details)
                    time.sleep(10)
                except Exception as ex:
                    print(ex)

            if not instances:
                print("Instances are still creating.")
                return
            instance_details_list = []
            time.sleep(30)
            for i in range(len(instances["Instances"])):
                instance = instances["Instances"][i]
                instance_id = instance["InstanceId"]
                print(f"Instance {instance_id} getting created..")
                # wait_for_instance_status(ec2_client, instance_id, REGION)
                join_ad_tag_value = (
                    [tag["Value"] for tag in tags if tag["Key"] == "JoinAD"][0]
                    if any(tag["Key"] == "JoinAD" for tag in tags)
                    else ""
                )
                cip_status = wait_for_bootstrappingtag(
                    ec2_client,
                    instance_id,
                    "cip-status",
                    max_attempts=120,
                    sleep_seconds=2,
                )
                print(f"cip_status: {cip_status}")
                if cip_status == "bootstrapping":
                    bootstrapping_run_time = calculate_elapsed_time(start_time)
                    print(f"bootstrapping_run_time: {bootstrapping_run_time}")
                instance_details = {
                    "account_id": ACCOUNT_ID,
                    "region": REGION,
                    "instance_id": instance_id,
                    "os": os_type,
                    "os_version": os_version,
                    "ami_id": ami_id,
                    "ami_name": ami_name,
                    "join_ad_tag_value": join_ad_tag_value,
                    "bootstrapping_runtime": bootstrapping_run_time,
                    "cip-status_tag_value": "",
                    "bootstrap_run_time": "",
                }
                instance_details_list.append(instance_details)
                # terminate_instance(ec2_client, instance_id, cip_status_tag_value)
            print("All instance's created and add boostrapping tag ..")
            return instance_details_list

        # Function to terminate instances
        def terminate_instance(ec2_client, instance_id, cip_status_value):
            try:
                if cip_status_value == "bootstrapped":
                    # Waiting to get ssm document status accuratly back to the console.
                    # Terminate the instance if the tag value is 'bootstrapped'
                    ec2_client.terminate_instances(InstanceIds=[instance_id])
                    print(f"Instance {instance_id} terminated successfully.")
                else:
                    print(
                        f"Instance {instance_id} not terminated. Missing or incorrect cip-status tag."
                    )
            except Exception as e:
                print(f"Failed to terminate instance {instance_id}: {e}")

        def monitor_instances(ec2_client, instance_ids):
            # Create empty lists to store instances with finished setup and instances still being setup
            finished_instances = []
            active_instances = instance_ids.copy()
            start_time = datetime.datetime.now()
            # Check the cip_status tag for each instance
            while active_instances:
                for instance_id in active_instances:
                    cip_status = wait_for_tag(
                        ec2_client,
                        instance_id,
                        "cip-status",
                        max_attempts=120,
                        sleep_seconds=10,
                    )
                    if cip_status in [
                        "bootstrapped",
                        "bootstrap-failed",
                        "bootstrap-skipped",
                    ]:
                        # Move instance to finished_instances list and remove from active_instances list
                        bootstrap_run_time = calculate_elapsed_time(start_time)
                        finished_instances.append(
                            {
                                "instance_id": instance_id,
                                "cip_status": cip_status,
                                "bootstrap_run_time": bootstrap_run_time,
                            }
                        )
                        active_instances.remove(instance_id)
                        # terminate_instance(ec2_client,instance_id,cip_status)
                time.sleep(2)  # Add a delay before checking again
            return finished_instances

        # Common tags for all scenarios
        common_tags = [{"Key": "JoinAD", "Value": "True"}]
        scenarios = []

        # Add separate scenarios for the load
        for os_type in [
            "RHEL920",
            "RHEL810",
            "RHEL8ARM",
            "RHEL790",
            "RHEL940",
            "SUSE12",
            "SUSE15",
            "WINDOWS22",
            "WINDOWS19",
            "WINDOWS16",
        ]:
            # for os_type in ["RHEL"]:
            scenarios.append(
                {
                    "os_type": os_type,
                    "tags": [
                        {
                            "Key": "Name",
                            "Value": f"SSMAutomation_Stress_Testing_{os_type}",
                        }
                    ]
                    + common_tags,
                }
            )

    # write instance details to CSV
    def run_parallel(scenarios, subnet_id):
        instances_details = []

        # Create ec2 client
        ec2_client = get_client_by_service(REGION, ACCOUNT_ID, ACCOUNT_NAME, "ec2")

        instance_details = create_instance(
            ec2_client,
            scenarios["os_type"],
            scenarios["tags"],
            instance_count,
            subnet_id,
            dry_run=False,
        )
        if instance_details:
            instances_details.append(instance_details)
        return instances_details

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

        class SubnetPicker:
            def __init__(self, items, _ec2_client):
                self.items = items
                self.index = 0
                self._ec2_client = _ec2_client

            def next_item(self):
                if not self.items:
                    return None  # Return None if the list is empty

                item = self.items[self.index]
                response = self._ec2_client.describe_subnets(SubnetIds=[item])
                self.index = (self.index + 1) % len(self.items)
                leftover_ip = response["Subnets"][0]["AvailableIpAddressCount"]
                print(f"subnet {item} has {leftover_ip} left")
                if leftover_ip <= instance_count:
                    item = self.items[self.index]

                return item

        subnet_picker = SubnetPicker(
            SUBNET_IDS, get_client_by_service(REGION, ACCOUNT_ID, ACCOUNT_NAME, "ec2")
        )
        futures = [
            executor.submit(run_parallel, scenario, subnet_picker.next_item())
            for scenario in scenarios
        ]

    # Get results from futures
    results = [future.result() for future in futures]
    # print(f"results:  {results}")
    instance_ids = []
    for sublist in results:
        for inner_list in sublist:
            for instance_dict in inner_list:
                instance_ids.append(instance_dict["instance_id"])


def append_cip_status(result_list, finished_instances):
    for sublist in result_list:
        for inner_list in sublist:
            for instance_dict in inner_list:
                for instance in finished_instances:
                    if instance_dict["instance_id"] == instance["instance_id"]:
                        instance_dict["cip-status_tag_value"] = instance["cip_status"]
                        instance_dict["bootstrap_run_time"] = instance[
                            "bootstrap_run_time"
                        ]
                        break  # Once cip_status is appended, move to the next result
    return result_list


ec2_client = get_client_by_service(REGION, ACCOUNT_ID, ACCOUNT_NAME, "ec2")
finished_instances = monitor_instances(ec2_client, instance_ids)
result_list_with_cip_status = append_cip_status(results, finished_instances)


def write_instance_details_to_csv(instance_details_list, output_csv_file):
    output_fieldnames = [
        "account_id",
        "region",
        "instance_id",
        "os",
        "os_version",
        "ami_id",
        "ami_name",
        "join_ad_tag_value",
        "bootstrapping_runtime",
        "cip-status_tag_value",
        "bootstrap_run_time",
    ]
    try:
        with open(output_csv_file, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(output_fieldnames)
            writer.writerows(instance_details_list)
        print("Instance details successfully written to CSV.")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
        print("Instance details successfully written to CSV.")
    except Exception as e:
        print(f"Error writing to CSV: {e}")


timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_csv_file = "instance_details_{}_{}.csv".format(ACCOUNT_NAME, timestamp)
flat_instances = [item for sublist in result_list_with_cip_status for item in sublist]

aggregated_list = []
[aggregated_list.extend(one) for one in flat_instances]

keys = aggregated_list[0].keys()

with open(
    f"instance_details_{ACCOUNT_NAME}_{timestamp}.csv", "w", newline=""
) as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(aggregated_list)
