#!/usr/bin/env python3
import logging
import boto3
from botocore.client import ClientError

# Set logger
logger = logging.getLogger(__name__)
Format = "[%(name)8s()] %(message)s"
logging.basicConfig(format=Format, level=logging.INFO)

# Input the list of Parent OUs
root_id = ""  # Parent OU ID
Parent_OUs = ["Unmanaged"]
Child_OUs = {"Unmanaged": ["DBaaS", "CaaS", "ROSA", "Incubation"]}


def main():
    try:
        # Set up the boto3 client for AWS Organizations
        logger.info("setting up boto3 client")
        org_client = boto3.client("organizations")
        for ou in Parent_OUs:
            response = org_client.create_organizational_unit(ParentId=root_id, Name=ou)
            logger.info(f"Creating OU {ou}")
            parent_ou_id = response["OrganizationalUnit"]["Id"]

            # Get the list of child OUs for the current parent OU
            children = Child_OUs[ou]

            logger.info(f"creating {children} OU under {ou}")

            # Loop through the list of child OUs and create each one under the current parent OU
            for child in children:
                response = org_client.create_organizational_unit(
                    ParentId=parent_ou_id, Name=child
                )
    except ClientError as e:
        logger.error(e)


if __name__ == "__main__":
    main()
