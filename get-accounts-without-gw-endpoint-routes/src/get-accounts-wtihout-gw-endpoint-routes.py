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
        return response["VpcEndpoints"]
    except Exception as e:
        logger.critical(f"Error describing gateway endpoint(s): {e}")
        raise e


def get_route_tables(subnet_id, region, spoke_session):
    ec2_client = spoke_session.client("ec2", region)
    try:
        response = ec2_client.describe_route_tables(
            Filters=[
                {"Name": "association.subnet-id", "Values": [subnet_id]},
            ],
        )
        return response["RouteTables"]
    except Exception as e:
        logger.error(f"Error retrieving route table IDs: {str(e)}")
        raise e


def get_subnet_ids(vpc_id, region_name, spoke_session):
    # Create an EC2 client
    ec2_client = spoke_session.client("ec2", region_name=region_name)

    # Describe subnets
    response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )

    # Extract subnet IDs with the specified name prefixes
    subnet_ids = []
    for subnet in response["Subnets"]:
        subnet_name = None
        for tag in subnet.get("Tags", []):
            if tag["Key"] == "Name":
                subnet_name = tag["Value"]
                break

        if not subnet_name.startswith("firewall-subnet-"):
            subnet_ids.append(subnet["SubnetId"])

    return subnet_ids


def get_stack_outputs(region, stack_name, spoke_session):
    cloudformation = spoke_session.client("cloudformation", region)
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        return {output["OutputKey"]: output["OutputValue"] for output in outputs}
    except ClientError as e:
        raise e


def get_accounts_metadata(account_type, environment_type):
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")
    table_name = [
        name
        for name in dynamodb.list_tables()["TableNames"]
        if name.endswith("DYN_METADATA")
    ][0]

    metadata_table = (
        boto3.Session().resource("dynamodb", region_name="eu-west-1").Table(table_name)
    )

    accounts = []
    filter_expression = (
        Attr("status").eq("Active")
        & Attr("account-type").eq(account_type)
        & Attr("environment-type").eq(environment_type)
    )

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


def check_routes(route_table, endpoints):
    routes = route_table["Routes"]
    endpoint_ids = [endpoint["VpcEndpointId"] for endpoint in endpoints]
    route_targets = [route["GatewayId"] for route in routes if "GatewayId" in route]
    if route_targets:
        for endpoint_id in endpoint_ids:
            if endpoint_id not in route_targets:
                return True

    return False


def lambda_handler(event, context):
    services = ["s3", "dynamodb"]

    account_type = event.get("account_type")
    environment_type = event.get("environment_type")

    logger.info(f"account_type: {account_type}. environment_type: {environment_type}")

    accounts = event.get(
        "accounts", get_accounts_metadata(account_type, environment_type)
    )
    accounts_filter = {"account", "account-name", "region"}
    filtered_list = [
        {key: d[key] for key in accounts_filter if key in d} for d in accounts
    ]
    print(filtered_list)

    logger.info(f"Accounts to action: {len(filtered_list)}")
    remaining_accounts = {"accounts": filtered_list.copy()}
    logger.info(remaining_accounts)
    for account_details in filtered_list:
        account = account_details["account"]
        account_name = account_details["account-name"]
        region = account_details["region"]

        spoke_target_role = f"arn:aws:iam::{account}:role/CIP_MANAGER"
        spoke_session = _get_role_session(
            target_role_arn=spoke_target_role,
            session_policy={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:Describe*",
                            "ec2:Get*",
                            "cloudformation:DescribeStacks",
                        ],
                        "Resource": "*",
                    },
                ],
            },
        )
        stack_name = f"{account_name}-NETWORK-STACK"
        stack_output = get_stack_outputs(region, stack_name, spoke_session)
        vpc_id = stack_output["VPC"]
        subnets = get_subnet_ids(vpc_id, region, spoke_session)
        for service_name in services:
            existing_endpoints = get_existing_endpoints(
                vpc_id, service_name, region, spoke_session
            )
            if existing_endpoints:
                for subnet in subnets:
                    route_tables = get_route_tables(subnet, region, spoke_session)
                    for route_table in route_tables:
                        route_not_found = check_routes(route_table, existing_endpoints)
                        if route_not_found:
                            logger.info(
                                f"Route not found for service {service_name} in {account_name}: {account}"
                            )
            else:
                continue
        for dict in remaining_accounts["accounts"]:
            if dict["account"] == account:
                remaining_accounts["accounts"].remove(dict)
        logger.info(f"remaining accounts: {len(remaining_accounts['accounts'])}")
        logger.info(remaining_accounts)

        if context.get_remaining_time_in_millis() < 60000:  # 60 seconds before timeout
            lambda_client = boto3.client("lambda")
            try:
                response = lambda_client.invoke(
                    FunctionName=context.function_name,
                    InvocationType="Event",
                    Payload=json.dumps(remaining_accounts),
                )
                logger.info(f"Lambda invoke response: {response}")
                return
            except Exception as e:
                logger.info(f"remaining account: {remaining_accounts['accounts']}")
                logger.error(f"Error invoking lambda: {e}")
                raise e
