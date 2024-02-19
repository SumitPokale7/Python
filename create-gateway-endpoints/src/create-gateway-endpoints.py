import boto3
import json
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Set logger
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)


def _get_role_session(target_role_arn: str, session_policy: str = None, **kwargs):
    try:
        credentials = boto3.client("sts").assume_role(
            RoleArn=target_role_arn,
            Policy=json.dumps(session_policy) if session_policy else None,
            RoleSessionName="AssumeRole-EndPoint"[0:64],
        )["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda",
                "Message": f"Error assuming role {target_role_arn}",
            }
        )
        raise e


def get_existing_endpoints(vpc_id, service_name, region, spoke_session):
    ec2_client = spoke_session.client("ec2", region)

    try:
        # Describe VPC endpoints filtering by the specified tag and vpc id
        response = ec2_client.describe_vpc_endpoints(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "vpc-endpoint-type", "Values": ["Gateway"]},
                {
                    "Name": "service-name",
                    "Values": [f"com.amazonaws.{region}.{service_name}"],
                },
            ],
        )
        # Extract the VPC endpoint IDs
        endpoint_ids = [
            endpoint["VpcEndpointId"] for endpoint in response["VpcEndpoints"]
        ]
        # Check if there are matching endpoints
        if endpoint_ids:
            logger.info(
                f"Endpoint already exists for {service_name} service. Nothing to do for this endpoint."
            )
            return endpoint_ids
        else:
            logger.info(
                f"No {service_name} service gateway endpoint found in the VPC. Proceeding to create endpoint."
            )
            return []
    except Exception as e:
        logger.critical(f"Error describing gateway endpoint(s): {e}")
        raise e


def get_stack_outputs(region, stack_name, spoke_session):
    cloudformation = spoke_session.client("cloudformation", region)
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        return {output["OutputKey"]: output["OutputValue"] for output in outputs}
    except ClientError as e:
        raise e


def create_vpc_endpoint(
    vpc_id, service_name, region, tags, route_table_ids, account, spoke_session
):
    """
    Creates a VPC endpoint for the given service name.
    """
    ec2_client = spoke_session.client("ec2", region)
    try:
        # Create VPC endpoint for the specified service with tags
        response = ec2_client.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName=f"com.amazonaws.{region}.{service_name}",
            RouteTableIds=route_table_ids,
            TagSpecifications=[{"ResourceType": "vpc-endpoint", "Tags": tags}],
        )
        VpcEndpointId = response["VpcEndpoint"]["VpcEndpointId"]
        logger.info(f"VPC endpoint created for {service_name}: {VpcEndpointId}")
    except Exception as e:
        logger.critical(f"Error creating VPC endpoint for {service_name}: {str(e)}")
        raise e


def update_ddb_field(account_name, service_name, value: bool):
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")
    table_name = [
        name
        for name in dynamodb.list_tables()["TableNames"]
        if name.endswith("DYN_METADATA")
    ][0]
    dynamodb.update_item(
        TableName=table_name,
        Key={"account-name": {"S": account_name}},
        UpdateExpression="SET #gw = :val",
        ExpressionAttributeNames={"#gw": f"network-{service_name}-gw-endpoint"},
        ExpressionAttributeValues={":val": {"BOOL": value}},
    )


def get_accounts_metadata(account_type, environment_type, service_name, update_ignore_accounts):
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")
    table_name = [
        name
        for name in dynamodb.list_tables()["TableNames"]
        if name.endswith("DYN_METADATA")
    ][0]

    metadata_table = boto3.Session().resource("dynamodb", region_name="eu-west-1").Table(table_name)

    accounts = []
    filter_expression = (
        Attr("status").eq("Active")
        & Attr("account-type").eq(account_type)
        & Attr("environment-type").eq(environment_type)
        & Attr(f"network-{service_name}-gw-endpoint").not_exists()
    )

    if not update_ignore_accounts:
        filter_expression = (filter_expression & Attr("network-ignore-update").not_exists())

    params = {"FilterExpression": filter_expression}
    while True:
        response = metadata_table.scan(**params)

        for item in response.get("Items", []):
            accounts.append(item)

        if not response.get("LastEvaluatedKey"):
            break

        params.update(
            {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
            }
        )
    return accounts


def get_route_table_ids(vpc_id, region, spoke_session):
    ec2_client = spoke_session.client("ec2", region)
    try:
        response = ec2_client.describe_route_tables(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
            ],
        )
        route_table_ids = [
                rt["RouteTableId"] for rt in response["RouteTables"]
                if {'Key': 'Name', 'Value': 'IGW-routetable'} not in rt['Tags']
            ]
        return route_table_ids
    except Exception as e:
        logger.error(f"Error retrieving route table IDs: {str(e)}")
        raise e


def parse_event(event):
    update_ignore_accounts = event.get('update_ignore_accounts', False)

    if not isinstance(update_ignore_accounts, bool):
        raise ValueError(f"update_ignore_update is not a bool. Received value type: {type(update_ignore_accounts)}.")

    return event['account_type'], event['environment_type'], event['service'], update_ignore_accounts


def lambda_handler(event, context):

    account_type, environment_type, service_name, update_ignore_accounts = parse_event(event)

    logger.info(f"account_type: {account_type}. environment_type: {environment_type}")

    accounts = get_accounts_metadata(account_type, environment_type, service_name, update_ignore_accounts)

    for account_details in accounts:
        account = account_details['account']
        account_name = account_details['account-name']
        region = account_details['region']
        status = account_details['status']

        logger.info(
            f"Processing account details - Account: {account}, Account Name: {account_name}, Region: {region}, Status: {status}"
        )

        spoke_target_role = f"arn:aws:iam::{account}:role/CIP_MANAGER"
        spoke_session = _get_role_session(
            target_role_arn=spoke_target_role,
            session_policy={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["ec2:*", "cloudformation:*"],
                        "Resource": "*",
                    },
                ],
            },
        )
        stack_name = f"{account_name}-NETWORK-STACK"
        stack_output = get_stack_outputs(region, stack_name, spoke_session)
        vpc_id = stack_output["VPC"]
        route_table_ids = get_route_table_ids(vpc_id, region, spoke_session)

        existing_service_endpoints = get_existing_endpoints(vpc_id, service_name, region, spoke_session)

        if not existing_service_endpoints:
            service_tags = [
                {"Key": "managed-by", "Value": "aws-platform-team"},
                {
                    "Key": "Name",
                    "Value": f"platform-{service_name}-gateway-endpoint",
                },
            ]
            try:
                create_vpc_endpoint(
                    vpc_id,
                    service_name,
                    region,
                    service_tags,
                    route_table_ids,
                    account,
                    spoke_session,
                )
            except Exception as e:
                logger.critical(
                    f"Error creating VPC endpoint for {service_name}: {str(e)}"
                )
                raise e
            try:
                update_ddb_field(account_name, service_name, True)
                logger.info("Service Metadata updated correctly with value True.")
            except Exception as e:
                logger.critical("Failed to update Metadata correctly.")
                raise e
        else:
            # Endpoint exists which must be customer deployed
            try:
                update_ddb_field(account_name, service_name, False)
                logger.info("Service Metadata updated correctly with value False.")
            except Exception as e:
                logger.critical("Failed to update Metadata correctly.")
                raise e
        if (
            context.get_remaining_time_in_millis() < 60000
        ):  # 60 seconds before timeout
            lambda_client = boto3.client("lambda")
            try:
                response = lambda_client.invoke(
                    FunctionName=context.function_name,
                    InvocationType="Event",
                    Payload=json.dumps(event),
                )
                logger.info(f"Lambda invoke response: {response}")
                return
            except Exception as e:
                logger.error(f"Error invoking lambda: {e}")
                raise e
