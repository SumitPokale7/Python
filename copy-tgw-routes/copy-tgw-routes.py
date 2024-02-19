#!/usr/bin/env python3
import logging
import boto3
from botocore.exceptions import ClientError
from argparse import ArgumentParser


# Set logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_client(service):
    """Creates a BOTO3 client using the correct target accounts Role."""
    client = boto3.client(service)
    return client


def main(master_rt_id, target_rt_id):
    logger.info(f"Copying routes from {master_rt_id} to {target_rt_id}")

    ec2_client = create_client("ec2")

    search_response = ec2_client.search_transit_gateway_routes(
        TransitGatewayRouteTableId=master_rt_id,
        Filters=[
            {
                "Name": "type",
                "Values": [
                    "static",
                ],
            },
            {
                "Name": "attachment.resource-type",
                "Values": [
                    "vpc",
                ],
            },
        ],
    )

    if search_response["AdditionalRoutesAvailable"]:
        logger.warning("TGW Route search result has MISSING additional routes.")

    for route in search_response["Routes"]:
        for attachment in route["TransitGatewayAttachments"]:
            try:
                ec2_client.create_transit_gateway_route(
                    DestinationCidrBlock=route["DestinationCidrBlock"],
                    TransitGatewayRouteTableId=target_rt_id,
                    TransitGatewayAttachmentId=attachment["TransitGatewayAttachmentId"],
                )
            except ClientError as e:
                # Handle if route already exists
                if e.response["Error"]["Code"] == "RouteAlreadyExists":
                    logger.info(
                        f"Route Already Exists: {route['DestinationCidrBlock']}"
                    )
                else:
                    logger.warning(f"ERROR trying to create route: {e}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-m",
        "--master",
        type=str,
        help="Master TGW route table id to copy from",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--target",
        type=str,
        help="Target TGW route table id to copy to",
        required=True,
    )
    args = parser.parse_args()

    main(args.master, args.target)
