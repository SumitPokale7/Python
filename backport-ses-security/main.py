import json
import logging
import boto3
import sys
from botocore.exceptions import ClientError

logging.basicConfig(
    filename="./ses-deployment.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))
DRY_RUN = False
HUB_NAME = "WH-00H1"
CENTRAL_LOG_ACCOUNT_ID = "458479718442"
ORGANIZATION_ID = "o-0id74l0mho"
SES_NAMING_PREFIX = "Catalog-SES-Security"
SES_PROXY_NAME = "SelfServiceResources-LMD_SES_PROXY"
SES_PROXY_ACCOUNT_ID = "886236176633"


ses_deployments_h3 = [
    ["162314969912", "WS-00XD", "eu-west-1", "bp.com"],
    # ["455883902045", "WS-01BP", "eu-west-1", "aral.de"],
    # ["455883902045", "WS-01BP", "eu-west-1", "bp.com"],
    # ["455883902045", "WS-01BP", "eu-west-1", "ampm.com"],
    # ["455883902045", "WS-01BP", "eu-west-1", "castrol.com"],
    # ["634109072684", "WS-01EM", "eu-west-1", "aral.de"],
    # ["634109072684", "WS-01EM", "eu-west-1", "bp.com"],
    # ["634109072684", "WS-01EM", "eu-west-1", "ampm.com"],
    # ["634109072684", "WS-01EM", "eu-west-1", "castrol.com"],
    ["266147415947", "WS-01I8", "eu-west-1", "bp.com"],
    ["685634837724", "WS-01D4", "eu-west-1", "bp.com"],
    ["980972407306", "WS-014Y", "eu-west-1", "bp.com"],
    ["574356330239", "WS-01E1", "eu-west-1", "bp.com"],
    ["246293249106", "WS-014Z", "eu-west-1", "bp.com"],
    ["850283412992", "WS-0150", "eu-west-1", "bp.com"],
    # ["186644776811", "WS-01PZ", "eu-west-2", "bp.com"],
    # ["290253176684", "WS-01QE", "eu-west-2", "bp.com"],
]

ses_deployments_h1 = [
    # ["886236176633", "WS-Z067", "bp.com", "eu-west-1"],
    # ["886236176633", "WS-Z067", "aral.com", "eu-west-1"],
    # ["886236176633", "WS-Z067", "castrol.nl", "eu-west-1"],
    ["886236176633", "WS-Z067", "bp.com", "eu-west-2"],
]
# IAM session policy for 'CIP_SelfService' role in the API Hub and Customer spoke account
ses_provision_policy_dict = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "ses:VerifyDomainIdentity",
                "ses:SetIdentityNotificationTopic",
                "ses:DeleteIdentity",
                "ses:ListIdentities",
                "ses:CreateEmailIdentity",
                "ses:DeleteEmailIdentity",
                "ses:GetEmailIdentity",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:CreateLogGroup",
                "logs:PutRetentionPolicy",
                "logs:DescribeSubscriptionFilters",
                "logs:DeleteSubscriptionFilter",
                "logs:PutSubscriptionFilter",
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunction",
                "lambda:ListFunctions",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:InvokeFunction",
                "events:PutRule",
                "events:DeleteRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "sns:CreateTopic",
                "sns:TagResource",
                "sns:Subscribe",
                "sns:DeleteTopic",
                "sns:GetTopicAttributes",
                "sns:Unsubscribe",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:CreatePolicy",
                "iam:AttachRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:PutRolePolicy",
                "iam:GetRolePolicy",
                "iam:PassRole",
                "iam:DeleteRole",
            ],
            "Resource": "*",
        },
    ],
}


def create_session(id_, policy=None, duration=900):
    """
    Creates a session policy is an inline policy on the fly
    and passes in the session during role assumption
    :param id_: account id
    :param policy: IAM inline policy
    :param duration: IAM session duration
    :return: boto3.session
    """

    try:
        dev_session = boto3.Session(profile_name=f"{HUB_NAME}-role_OPERATIONS")
        target_role = f"arn:aws:iam::{id_}:role/AWS_PLATFORM_ADMIN"
        logger.debug(f"Assuming role: {target_role}")
        credentials = dev_session.client("sts").assume_role(
            DurationSeconds=duration,
            Policy=json.dumps(policy) if policy else None,
            RoleArn=target_role,
            RoleSessionName="AssumeRole-CIPSelfService"[0:64],
        )["Credentials"]
        return boto3.session.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    except ClientError as e:
        logger.critical(
            {
                "Code": "ERROR Lambda SelfServiceResources Service",
                "Message": f"Error assuming role {target_role} ",
            }
        )
        raise e


def get_destination_datastream(lambda_client, function_name, payload=None):
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(payload),
        )
        response_payload = json.loads(response["Payload"].read().decode("utf-8"))
        logger.info(f"response from ses_proxy:{response_payload}")
        return response_payload["response"]
    except ClientError as e:
        logger.error(e, exc_info=True)
        raise


def aws_session(service: str, region: str, spoke_account_id: str) -> object:
    """
    Creates AWS Session
    region: sets the aws region for boto3 session
    service: aws service to create boto3 client with
    spoke_account_id: customer spoke id
    """
    try:
        return create_session(spoke_account_id, ses_provision_policy_dict).client(
            service, region_name=region
        )
    except Exception as err:
        logger.info("Exception creating aws_session")
        raise ValueError(f"expecting creating AWS session, {err}")


def check_identity_exist(ses_client, ses_identity):
    response = ses_client.list_identities(
        IdentityType="Domain",
    )
    ses_identity_exists = False
    for identity in response["Identities"]:
        if identity == ses_identity:
            ses_identity_exists = True
    return ses_identity_exists


def deploy_ses_security(
    region, spoke_account_id, spoke_account_name, ses_identity, dry_run
):
    logger = logging.getLogger(__name__)

    logger.info(f"Spoke account id: {spoke_account_id}")
    ses_client = aws_session("ses", region, spoke_account_id)

    # LMD_PROXY is only deployed to eu-west-1
    lambda_client = aws_session("lambda", "eu-west-1", SES_PROXY_ACCOUNT_ID)

    ses_identity_name = ses_identity.replace(".", "_")
    resources_prefix = f"{SES_NAMING_PREFIX}-{ses_identity_name}-{spoke_account_name}"
    cloudformation_client = aws_session("cloudformation", region, spoke_account_id)
    stack_name = f"{resources_prefix}-{region}-CFN-SES".replace("_", "-")
    if not check_identity_exist(ses_client, ses_identity):
        logger.info(
            f"SES identity {ses_identity} does not exist in {region}, Nothing to do"
        )
        return
    # reading destination arn for the subscription filter
    if dry_run:
        logger.info(f"DRY_RUN: for domain {ses_identity} in {region}")
        return
    request_payload = {"AccountId": spoke_account_id, "OrgId": ORGANIZATION_ID}
    response = get_destination_datastream(
        lambda_client, SES_PROXY_NAME, request_payload
    )
    if response["statusCode"] != 200:
        logger.error(f"ses proxy call failed:{response['ErrorMessage']}")
        raise
    subs_filter_destination = response["SesBucket"]
    destination_log_arn = f"arn:aws:logs:{region}:{CENTRAL_LOG_ACCOUNT_ID}:destination:{subs_filter_destination}"

    logger.info(f"destination_log_arn:{destination_log_arn}")

    with open("templates/ses-security.yaml") as template_fileobj:
        template_data = template_fileobj.read()
    cloudformation_client.validate_template(TemplateBody=template_data)

    response_create = cloudformation_client.create_stack(
        StackName=stack_name,
        TemplateBody=template_data,
        Parameters=[
            {
                "ParameterKey": "NamingPrefix",
                "ParameterValue": resources_prefix,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "AccountName",
                "ParameterValue": spoke_account_name,
                "UsePreviousValue": True,
            },
        ],
        EnableTerminationProtection=False,
        Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
    )
    stack_id = response_create["StackId"]
    cloudformation_client.get_waiter("stack_create_complete").wait(
        StackName=stack_id, WaiterConfig={"Delay": 10, "MaxAttempts": 84}
    )

    response = cloudformation_client.describe_stacks(StackName=stack_id)
    outputs = response["Stacks"][0].get("Outputs", [])
    for output in outputs:
        keyName = output["OutputKey"]
        if keyName == "BounceSNSTopicArn":
            bounce_sns_arn = output["OutputValue"]
        elif keyName == "ComplaintSNSTopicArn":
            complaint_sns_arn = output["OutputValue"]
        elif keyName == "DeliverySNSTopicArn":
            delivery_sns_arn = output["OutputValue"]

    # Create Log groups
    log_groups = [
        f"/aws/lambda/{resources_prefix}-LMD_SNSLogForwarder/bounce",
        f"/aws/lambda/{resources_prefix}-LMD_SNSLogForwarder/complaint",
        f"/aws/lambda/{resources_prefix}-LMD_SNSLogForwarder/delivery",
        f"/aws/lambda/{resources_prefix}-LMD_SNSLogForwarder",
    ]
    logs_client = aws_session("logs", region, spoke_account_id)
    for log_group in log_groups:
        try:
            logs_client.create_log_group(logGroupName=log_group)
            logs_client.put_retention_policy(logGroupName=log_group, retentionInDays=90)
        except logs_client.exceptions.ResourceAlreadyExistsException:
            logger.info(f"Log group {log_group} already exists")
            pass

        place_to_slice = log_group.rfind("SNSLogForwarder/")

        if place_to_slice == -1:
            continue

        filter_name = (
            f"{log_group[place_to_slice:]}-{resources_prefix}-subscription-filter"
        )

        # create subscription filters
        logs_client.put_subscription_filter(
            logGroupName=log_group,
            filterName=filter_name,
            filterPattern="",
            destinationArn=destination_log_arn,
        )

        logger.info(f"subscription filter {filter_name} created successfully")

    # set identity notifications
    ses_client.set_identity_notification_topic(
        Identity=ses_identity, NotificationType="Bounce", SnsTopic=bounce_sns_arn
    )
    ses_client.set_identity_notification_topic(
        Identity=ses_identity, NotificationType="Complaint", SnsTopic=complaint_sns_arn
    )
    ses_client.set_identity_notification_topic(
        Identity=ses_identity, NotificationType="Delivery", SnsTopic=delivery_sns_arn
    )


def main(dry_run=DRY_RUN):
    print("Starting Backport SES")
    ses_deployments = ses_deployments_h1

    for domain in ses_deployments:
        try:
            spoke_account_id = domain[0]
            spoke_account_name = domain[1]
            ses_identity = domain[2]
            region = domain[3]
            logger.info(f"Deploying SES security for {ses_identity} in {region}")
            deploy_ses_security(
                region, spoke_account_id, spoke_account_name, ses_identity, dry_run
            )
        except Exception as e:
            print(e)
            print("Error", domain, region)
            pass


if __name__ == "__main__":
    main()
