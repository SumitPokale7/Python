import csv
import logging
from botocore.exceptions import ClientError, ParamValidationError
import boto3

# Configure logger
logging.basicConfig(filename='ec2_instance_errors.log', level=logging.INFO)
logger = logging.getLogger(__name__)


def get_ec2_instance_info(instance_ids):
    """
    Retrives OS information of Name & Version for an EC2 instance.
    """
    ssm_client = boto3.client('ssm')
    instance_info_map = {}
    chunk_size = 50
    unreachable_instances = []  # Track unreachable instances
    try:
        for i in range(0, len(instance_ids), chunk_size):
            chunk_instance_ids = instance_ids[i:i+chunk_size]
            response = ssm_client.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': chunk_instance_ids}])
            instance_info_list = response.get('InstanceInformationList', [])
            for info in instance_info_list:
                instance_id = info.get('InstanceId')
                platform_name = info.get('PlatformName')
                platform_version = info.get('PlatformVersion')
                if instance_id and platform_name and platform_version:
                    instance_info_map[instance_id] = (platform_name, platform_version)

            unreachable_instances.extend(set(chunk_instance_ids) - {info.get('InstanceId') for info in instance_info_list})
        if unreachable_instances:
            logger.error(f"Unreachable instances: {unreachable_instances}")
        return instance_info_map, unreachable_instances
    except (ClientError, ParamValidationError) as e:
        logger.error(f"Error retrieving OS information for instances: {e}")
        return instance_info_map, instance_ids  # Return instance IDs that couldn't be queried


def get_all_ec2_instance_ids(ec2_client):
    """
    Retrieves IDs of all EC2 instances.
    """
    instance_ids = []
    paginator = ec2_client.get_paginator('describe_instances')
    try:
        response_iterator = paginator.paginate()
        for page in response_iterator:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])
        return instance_ids
    except Exception as e:
        logger.error(f"Error retrieving EC2 instances: {e}")


def get_os_flavors(instance_info_map):
    """
    Retrieves the OS flavor and major version for each instance.
    """
    os_flavors = {}
    error_instances = []
    for instance_id, (platform_name, platform_version) in instance_info_map.items():
        try:
            os_flavor = f"{platform_name} {platform_version.split('.')[0]}"
            os_flavors[instance_id] = os_flavor
        except ValueError as e:
            logger.error(f"Error processing instance {instance_id}: {e}")
            error_instances.append((instance_id, e))
    return os_flavors, error_instances


def write_to_csv(data, filename):
    """
    Writes data to a CSV file.
    """
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ["Environment", "Instance ID", "OS", "Major Version"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for environment, instance_id, os_name, major_version in data:
            writer.writerow({'Environment': environment, 'Instance ID': instance_id, 'OS': os_name, 'Major Version': major_version})


def main():
    ec2_client = boto3.client('ec2')
    instance_ids = get_all_ec2_instance_ids(ec2_client)
    instance_info_map, unreachable_instances = get_ec2_instance_info(instance_ids)
    os_flavors, error_instances = get_os_flavors(instance_info_map)

    instance_tags = {}
    for instance_id in instance_ids:
        try:
            response = ec2_client.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [instance_id]},
                                                         {'Name': 'key', 'Values': ['cloud-environment']}])
            for tag in response['Tags']:
                if tag['Key'] == 'cloud-environment':
                    instance_tags[instance_id] = tag['Value']
                    break
        except Exception as e:
            logger.error(f"Error retrieving tags for instance {instance_id}: {e}")
            error_instances.append((instance_id, e))

    output_data = [(instance_tags.get(instance_id, 'Unknown'), instance_id, ' '.join(os_flavor.split()[:-1]), os_flavor.split()[-1])
                   if len(os_flavor.split()) > 2 else (instance_tags.get(instance_id, 'Unknown'), instance_id, os_flavor.split()[0], os_flavor.split()[1])
                   for instance_id, os_flavor in os_flavors.items()]

    write_to_csv(output_data, 'ec2_instance_info.csv')

    # Log success message
    logger.info("Results written to ec2_instance_info.csv")

    # Log report on unreachable instances
    if unreachable_instances:
        logger.error(f"Could not query information for {len(unreachable_instances)} instances: {unreachable_instances}")


if __name__ == '__main__':
    main()
