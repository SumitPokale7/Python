from botocore.exceptions import ClientError
import boto3
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global product_name, product_id, status

LONG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def create_creds(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="LambdaInventorySession"
    )


def create_client(
    service: str, role: str, region: str, hub_session: boto3.session.Session
):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        creds = create_creds(role, hub_session)
        client = boto3.client(
            service,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        logger.error(f"cannot assume the role: {e}")
        raise e

    return client


def convert_date_str(date_, format_=LONG_DATE_FORMAT):
    """Convert date to string"""
    date_str = date_.strftime(format_)
    return date_str


def extract_provisioned_products(
    session: boto3.session.Session, _account_id: str = None, _region: str = "eu-west-1"
):
    try:
        # iterate over only spoke accounts
        if _account_id:
            target_role_arn = f"arn:aws:iam::{_account_id}:role/CIP_INSPECTOR"
            sc_client = create_client(
                "servicecatalog", target_role_arn, _region, session
            )
        # iterate over only hub account
        else:
            sc_client = session.client("servicecatalog")

        response = sc_client.search_provisioned_products(
            Filters={
                "SearchQuery": [
                    "productName:SelfServiceResources-SC-PRODUCT-SHARE-AD-CONNECTOR"
                ],
            }
        )
        for response in response["ProvisionedProducts"]:
            if response["Name"]:
                account_id = _account_id
                product_name = response["Name"]
                product_id = response["Id"]
                status = response["Status"]
                logger.info(
                    f"Following ServiceCatalog mark for deletion: {product_name} / {product_id} in  {account_id} with the status: {status}"
                )

            # Only uncomment if you need to remove the SC's
            # logger.info(sc_client.client.terminate_provisioned_product(
            #     ProvisionedProductName=product_name
            # ))

            else:
                logger.info(
                    "No Service catelog with the name SelfServiceResources-SC-PRODUCT-SHARE-AD-CONNECTOR"
                )

        return [
            {
                "account_id": _account_id,
                "product_name": response["Name"],
                "product_id": response["Id"],
                "status": response["Status"],
            }
            for response in response["ProvisionedProducts"]
        ]

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{target_role_arn} because of {err}"
            )
            return None
        else:
            raise err
