#!/usr/bin/env python3
import logging
import boto3
from botocore.client import ClientError

# Set logger
logger = logging.getLogger(__name__)
FORMAT = "[%(name)8s()] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

# Create a list of parent OUs to create
parent_ous = ["CoreProducts", "LegacyProducts", "PlatformServices", "Unmanaged"]

# Create a dictionary of child/layer 2 OUs, with the key being the parent OU and the value being a list of child OUs
child_ous = {
    "CoreProducts": ["Connected", "Standalone", "Sandbox", "Foundation"],
    "LegacyProducts": ["EnterpriseProd", "EnterpriseNonProd"],
    "PlatformServices": ["SharedServices", "Bin", "Hub"],
    "Unmanaged": ["DBaaS", "CaaS", "ROSA", "Incubation"],
}

# Create a dictionary of child/layer 3 OUs, with the key being the parent OU and the value being a list of child OUs
sub_child_ous = {
    "Connected": [
        "ConnectedProd1",
        "ConnectedProd2",
        "ConnectedProd3",
        "ConnectedProd4",
        "ConnectedProd5",
        "ConnectedNonProd1",
        "ConnectedNonProd2",
        "ConnectedNonProd3",
        "ConnectedNonProd4",
        "ConnectedNonProd5",
    ],
    "Standalone": [
        "StandaloneProd1",
        "StandaloneProd2",
        "StandaloneProd3",
        "StandaloneNonProd1",
        "StandaloneNonProd2",
        "StandaloneNonProd3",
    ],
    "Sandbox": [],
    "Foundation": ["FoundationProd", "FoundationNonProd"],
    "EnterpriseProd": [],
    "EnterpriseNonProd": [],
    "SharedServices": [],
    "Bin": [],
    "Hub": [],
    "DBaaS": [],
    "CaaS": [],
    "ROSA": [],
    "Incubation": [],
}

# Loop through the list of parent OUs and create each one


def main():
    try:
        # Set up the boto3 client for AWS Organizations
        logger.info("setting up boto3 client")
        org_client = boto3.client("organizations")
        # Getting root OU ID
        root_id = org_client.list_roots()["Roots"][0]["Id"]

        for parent_ou in parent_ous:
            try:
                logger.info(f"Creating Layer 1 OU {parent_ou}")
                response = org_client.create_organizational_unit(
                    ParentId=root_id, Name=parent_ou
                )
                logger.info(f"{parent_ou} successfully created")
                parent_ou_id = response["OrganizationalUnit"]["Id"]

                # Get the list of child OUs for the current parent OU
                children = child_ous[parent_ou]
                if not children == []:
                    logger.info(f"creating {children} OU under {parent_ou}")

                    # Loop through the list of child OUs and create each one under the current parent OU
                    for child in children:
                        response = org_client.create_organizational_unit(
                            ParentId=parent_ou_id, Name=child
                        )
                        child_ou_id = response["OrganizationalUnit"]["Id"]
                        logger.info(
                            f'Created child OU "{child}" with ID "{child_ou_id}" under parent OU "{parent_ou}"'
                        )
                        sub_childs = sub_child_ous[child]
                        if not sub_childs == []:
                            logger.info(f"creating OUs {sub_childs} under {child}")
                            for sub_child in sub_childs:
                                response = org_client.create_organizational_unit(
                                    ParentId=child_ou_id, Name=sub_child
                                )
                                sub_child_ou_id = response["OrganizationalUnit"]["Id"]
                                logger.info(
                                    f'Created child OU "{sub_child}" with ID "{sub_child_ou_id}" under parent OU "{child_ou_id}"'
                                )
                        else:
                            logger.info(f"list is empty for layer 3 OU under {child}")

                    print(f'Created parent OU "{parent_ou}" with ID "{parent_ou_id}"')
                else:
                    logger.info("Layer 2 OU list is empty")
            except ClientError as client_error:
                if (
                    client_error.response["Error"]["Code"]
                    == "DuplicateOrganizationalUnitException"
                ):
                    logger.info("The OU already exists. No action taken.")
                    continue
                else:
                    logger.error(client_error)

    except ClientError as client_error:
        logger.error(client_error)

    except Exception as e:
        logger.info(e)


if __name__ == "__main__":
    main()
