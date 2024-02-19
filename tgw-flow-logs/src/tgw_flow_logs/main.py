"""
This function creates Transit GateWay flow logs.
"""
import os
import logging
import boto3
import aws_lambda_logging

aws_lambda_logging.setup(level="INFO", boto_level="CRITICAL")
logger = logging.getLogger()


def lambda_handler(event, context):
    logger.info("New event received")
    logger.info(event)

    s3_arn = os.environ["s3_arn"]

    log_format = "${version} ${account-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} \
     ${protocol} ${packets} ${bytes} ${start} ${end} ${log-status} ${tcp-flags} ${type} \
     ${region} ${pkt-src-aws-service} ${pkt-dst-aws-service} ${flow-direction}"
    try:
        for region, tgw_id in event.items():
            client = boto3.client("ec2", region_name=region)
            response = client.create_flow_logs(
                ResourceIds=[tgw_id],
                ResourceType="TransitGateway",
                LogDestinationType="s3",
                LogDestination=s3_arn,
                LogFormat=log_format,
            )
            logger.info(response)
    except Exception as e:
        logger.error(e, exc_info=True)
        logger.critical(
            {
                "Code": "ERROR TGW-MANAGEMENT-Service-001",
                "Message": "TGW flow log creation failed for TGW",
            }
        )
