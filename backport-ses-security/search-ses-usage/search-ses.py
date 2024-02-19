"""
search-ses.py: Check ses created without Service Catalog
"""
import sys
import logging

import boto3

SPOKE_ROLE = "CIP_INSPECTOR"
HUB_NAME = "WH-00H3"
logging.basicConfig(
    filename="./ses-logfile.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_session(account_id, spoke_role):
    dev_session = boto3.Session(profile_name=f"{HUB_NAME}-role_READONLY")
    sts_client = dev_session.client("sts")
    assumed_role_object = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{spoke_role}",
        RoleSessionName="InvestigateSES",
    )
    credentials = assumed_role_object["Credentials"]
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    return session


accounts_h3 = [
    "290253176684",
    "186644776811",
    "511245123732",
    "208545751392",
    "532163301520",
    "140390956842",
    "162314969912",
    "455883902045",
    "634109072684",
    "439344466251",
    "74520126643",
    "115677494026",
    "994061858128",
    "467722407474",
    "596935770041",
    "266147415947",
    "705740769445",
    "43969524981",
    "749566913576",
    "330428337682",
    "685634837724",
    "550622295554",
    "980972407306",
    "694925389833",
    "574356330239",
    "689100415056",
    "586471617173",
    "246293249106",
    "850283412992",
    "728865574843",
    "157912730375",
    "543636225110",
    "639836084840",
    "274088022707",
    "506035479554",
    "614577381613",
    "829651645867",
    "853457969456",
]
accounts_h2 = ["891244521389", "899634452187"]
accounts_h1 = ["886236176633", "161982214036"]


def is_verified(region, session, identity):
    ses_client = session.client("ses", region_name=region)
    response = ses_client.get_identity_verification_attributes(Identities=[identity])
    if response["VerificationAttributes"][identity]["VerificationStatus"] == "Success":
        return True
    return False


def list_identities(region, session):
    ses_client = session.client("ses", region_name=region)
    response = ses_client.list_identities(
        IdentityType="Domain",
    )
    return response


def main():
    print("Starting SES search")
    regions = ["us-east-2", "us-east-1", "eu-west-2", "eu-west-1"]
    for account in accounts:
        try:
            session = get_session(account, SPOKE_ROLE)
        except Exception as e:
            logger.error(e)
            logger.error("Error getting session", account)
            continue
        for region in regions:
            try:
                response = list_identities(region, session)
                if response["Identities"] != []:
                    for identity in response["Identities"]:
                        if is_verified(region, session, identity):
                            print(f"{account},{region},{identity}")
            except Exception as e:
                print(e)
                print("Error", account, region)
                pass


if __name__ == "__main__":
    accounts = accounts_h3
    main()
