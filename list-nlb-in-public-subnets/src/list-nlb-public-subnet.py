import json
import boto3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb", region_name="eu-west-1")
lambda_client = boto3.client("lambda")

table_name = next(
    name
    for name in dynamodb_client.list_tables()["TableNames"]
    if name.endswith("DYN_METADATA")
)


def lambda_handler(event, context):
    try:
        logger.info(event)
        account_type = event["account-type"]
        remaining_accounts = event.get("remaining_accounts", None)
        result_list = event.get("result_list", [])

        if remaining_accounts:
            list_accounts = get_accounts_by_numbers(remaining_accounts)
        else:
            list_accounts = get_spokes(account_type)
            remaining_accounts = [account["account"]["S"] for account in list_accounts].copy()
        for account in list_accounts:
            account_number = account["account"]["S"]
            account_name = account["account-name"]["S"]
            role = f"arn:aws:iam::{account_number}:role/CIP_MANAGER"
            region = account["region"]["S"]

            client_ec2 = create_client("ec2", role, region)
            client_elb = create_client("elbv2", role, region)

            subnet_list_in_account = {
                subnet["SubnetId"]
                for subnet in client_ec2.describe_subnets(
                    Filters=[{"Name": "tag:Name", "Values": ["public-subnet-*"]}]
                )["Subnets"]
            }
            describe_elb = client_elb.describe_load_balancers()
            processed_nlbs = set()
            if not describe_elb.get("LoadBalancers"):
                logger.info(
                    f"No ELB found in account {account_number} in region {region}"
                )
            else:
                for elb in describe_elb["LoadBalancers"]:
                    if (
                        elb["Type"] == "network"
                        and elb["LoadBalancerName"] not in processed_nlbs
                    ):
                        for lb_az in elb["AvailabilityZones"]:
                            if lb_az["SubnetId"] in subnet_list_in_account:
                                logger.info(
                                    f"NLB {elb['LoadBalancerName']} found in account {account_number} in region {region}, in subnet {lb_az['SubnetId']}"
                                )
                                result_list.append(
                                    f"{account_number}  {account_name}  {elb['LoadBalancerName']}  {region}"
                                )
                                processed_nlbs.add(elb["LoadBalancerName"])
                                break
                        else:
                            logger.info(
                                f"No NLB found in account {account_number} in region {region}"
                            )
            remaining_accounts.remove(account_number)

            # Check remaining time and reinvoke if necessary
            if context.get_remaining_time_in_millis() < 30000:  # 30 seconds buffer
                if remaining_accounts:
                    logger.info(
                        f"Reinvoking Lambda for {len(remaining_accounts)} remaining accounts"
                    )
                    lambda_client.invoke(
                        FunctionName=context.function_name,
                        InvocationType="Event",
                        Payload=json.dumps(
                            {
                                "account-type": account_type,
                                "remaining_accounts": remaining_accounts,
                                "result_list": result_list,
                            }
                        ),
                    )
                    return
        logger.info(f"Final Result List: {result_list}")
    except Exception as e:
        logger.error(
            f"Error processing event: {e}, Remaining accounts: {remaining_accounts}, Result list so far: {result_list}"
        )


def create_creds(role, session_policy):
    sts_client = boto3.client("sts")
    return sts_client.assume_role(
        RoleArn=role,
        RoleSessionName="list-nlb",
        Policy=json.dumps(session_policy) if session_policy else None,
    )


def create_client(service, role, region):
    session_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeSubnets",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elbv2:DescribeLoadBalancers",
                    "ec2:DescribeNetworkInterfaces",
                ],
                "Resource": "*",
            },
        ],
    }
    creds = create_creds(role, session_policy)
    return boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name=region,
    )


def get_spokes(account_type):
    if account_type == "Standalone":
        params = {}
        params = {
            "TableName": table_name,
            "FilterExpression": "#account_type = :account_type AND #status = :status",
            "ExpressionAttributeNames": {
                "#account_type": "account-type",
                "#status": "status",
            },
            "ExpressionAttributeValues": {
                ":account_type": {"S": account_type},
                ":status": {"S": "Active"},
            },
        }
    elif account_type == "Connected":
        params = {
            "TableName": table_name,
            "FilterExpression": "#account_type = :account_type AND #status = :status AND #internet_facing = :internet_facing AND #network_web_only = :network_web_only",
            "ExpressionAttributeNames": {
                "#account_type": "account-type",
                "#internet_facing": "internet-facing",
                "#network_web_only": "network-web-only",
                "#status": "status",
            },
            "ExpressionAttributeValues": {
                ":account_type": {"S": account_type},
                ":internet_facing": {"BOOL": True},
                ":network_web_only": {"BOOL": True},
                ":status": {"S": "Active"},
            },
        }

    result = []
    count = 0
    while True:
        response = dynamodb_client.scan(**params)
        result.extend(response.get("Items", []))
        count += len(response.get("Items", []))
        if not response.get("LastEvaluatedKey"):
            break
        params["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info(f"Total active accounts found of {account_type} type are: {count}")
    return result


def get_accounts_by_numbers(account_numbers):
    result = []
    for account_number in account_numbers:
        response = dynamodb_client.scan(
            TableName=table_name,
            FilterExpression="#account = :account_number",
            ExpressionAttributeValues={":account_number": {"S": account_number}},
            ProjectionExpression="#account, #account_name, #region",
            ExpressionAttributeNames={
                "#account": "account",
                "#account_name": "account-name",
                "#region": "region",
            },
        )
        if "Items" in response:
            result.extend(response["Items"])
    return result
