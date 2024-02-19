import sys
import logging
import boto3
import distutils.util
import json
from argparse import ArgumentParser

SPOKE_ROLE = "AWS_PLATFORM_OPERATIONS"
HUB_NAME = "WH-00H1"
logging.basicConfig(
    filename=f"./fw_rules-{HUB_NAME}-logfile.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_session(account_id, spoke_role, region):
    try:
        dev_session = boto3.Session(profile_name=f"{HUB_NAME}-role_SPOKE-OPERATIONS")
        sts_client = dev_session.client("sts")
        assumed_role_object = sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{account_id}:role/{spoke_role}",
            RoleSessionName="networkfirewall",
        )
        credentials = assumed_role_object["Credentials"]
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
        return session
    except Exception as e:
        logger.error(e)


def main(args):
    input_file = args.inputfile
    dry_run = args.dry_run
    try:
        with open(input_file, "r") as file:
            # Read the  content of the file
            content = file.read()
            lines = content.split("\n")
            for line in lines:
                delete_firewall_rules(line, dry_run)

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def delete_firewall_rules(data, dry_run):
    mydata = data.split(",")
    logger.info(mydata)
    rule_arn = mydata[0]
    account = mydata[1]
    region = mydata[2]

    try:
        session = get_session(account, SPOKE_ROLE, region)
    except Exception as e:
        logger.error(e)
        logger.error("Error getting session", account)
    try:
        if dry_run:
            response = firewall_rule_group(session, rule_arn)
            logger.info(response)
            is_deleted = check_rule(response, session)
            logger.info(
                f"DRY RUN: Confirming deletion of the firewall_rule_group_association '{is_deleted}' "
            )
        else:
            response = firewall_rule_group(session, rule_arn)
            logger.info(response)
            is_deleted = check_rule(response, session)
            if is_deleted:
                response = firewall_rule_group_delete(session, rule_arn)
                logger.info(response)

    except Exception as e:
        logger.error(e)
        pass


def firewall_rule_group(session, rule_arn):
    network_client = session.client("route53resolver")
    response = network_client.get_firewall_rule_group_association(
        FirewallRuleGroupAssociationId=rule_arn
    )
    return response


def firewall_rule_group_delete(session, rule_arn):
    network_client = session.client("route53resolver")
    response = network_client.disassociate_firewall_rule_group(
        FirewallRuleGroupAssociationId=rule_arn
    )
    return response


def check_rule(data, session):
    json_string = json.dumps(data, indent=2)
    parsed_data = json.loads(json_string)

    # Access specific values
    # association_id = parsed_data['FirewallRuleGroupAssociation']['Id']
    rule_group_id = parsed_data["FirewallRuleGroupAssociation"]["FirewallRuleGroupId"]
    try:
        network_client = session.client("route53resolver")
        response = network_client.list_firewall_rules(FirewallRuleGroupId=rule_group_id)
        logger.info(response)
        return False
    except Exception as e:
        logger.error(e)
        return True


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "-e",
        "--inputfile",
        type=str,
        help="Provide args file path",
        required=True,
    )
    parser.add_argument("--dry-run", type=distutils.util.strtobool, default="true")
    args = parser.parse_args()
    main(args)
