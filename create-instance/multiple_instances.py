import boto3
import csv
import os
from typing import Final

# Read the variables from the CSV file
csv_file_path = "account_details.csv"

input_account_name: Final = os.getenv("Account_Name", "WS-Y0T0")
DryRun: Final = os.getenv("Dry_Run", "False")
tags = [{"Key": "Name", "Value": "Amazon-SP"}]

with open(csv_file_path, mode="r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if row["ACCOUNT_NAME"] == input_account_name:
            ACCOUNT_NAME = row["ACCOUNT_NAME"]
            ACCOUNT_ID = row["ACCOUNT_ID"]
            REGION = row["REGION"]
            SECURITY_GROUP_ID = row["SECURITY_GROUP_ID"]
            SUBNET_ID = row["SUBNET_ID"]
            AMI_ID = row["AMI_ID"]

            INSTANCE_PROFILE = f"{ACCOUNT_NAME}-role_INSTANCE"
            basedir = os.path.abspath(os.path.dirname(__file__))
            _UserData = os.path.join(basedir, "EC2LinuxUserData.sh")
        basedir = os.path.abspath(os.path.dirname(__file__))
        _UserData = os.path.join(basedir, "EC2LinuxUserData.sh")


def getUserData():
    with open(_UserData, "r") as f:
        return f.read()


# Initialize a session using Amazon EC2 resource and client
ec2_resource = boto3.resource("ec2", region_name=REGION)
ec2_client = boto3.client("ec2", region_name=REGION)

# eni_count = 2  # Number of secondary ENIs to create
# secondary_network_interfaces = []

# for i in range(eni_count):
#     # Create secondary ENI
#     eni_response = ec2_resource.create_network_interface(
#         SubnetId=SUBNET_ID,
#         Groups=[SECURITY_GROUP_ID]
#     )
#     eni_id = eni_response.id
#     secondary_network_interfaces.append({
#         'NetworkInterfaceId': eni_id,
#         'DeviceIndex': i + 1,  # DeviceIndex 0 is for the primary ENI

#     })

instance_response = ec2_client.run_instances(
    ImageId=AMI_ID,
    InstanceType="t3.large",
    MinCount=1,
    MaxCount=1,
    UserData=getUserData(),
    IamInstanceProfile={"Name": INSTANCE_PROFILE},
    SecurityGroupIds=[SECURITY_GROUP_ID],
    SubnetId=SUBNET_ID,
    # NetworkInterfaces=[
    #     {
    #         'DeviceIndex': 0,
    #         'SubnetId': SUBNET_ID,
    #         'Groups': [SECURITY_GROUP_ID],
    #         'AssociatePublicIpAddress': False,
    #         'DeleteOnTermination': True,
    #         'SecondaryPrivateIpAddressCount':eni_count,
    #     }
    # ] ,
    # + secondary_network_interfaces,
    TagSpecifications=[{"ResourceType": "instance", "Tags": tags}],
)

instance_id = instance_response["Instances"][0]["InstanceId"]

# Wait for the instance to enter the running state
instance = ec2_resource.Instance(instance_id)
instance.wait_until_running()
# Reload the instance attributes
instance.load()

print("Primary ENI IP:", instance.private_ip_address)

for network_interface in instance.network_interfaces:
    print(
        f"ENI ID: {network_interface.id}, Private IP Address: {network_interface.private_ip_address}"
    )
