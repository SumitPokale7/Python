import logging
import datetime
import boto3
from botocore.exceptions import ClientError
import argparse
import time

logging.basicConfig(
    filename=f"unshare-and-delete-sc-portfolio-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")


def assume_role(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="SC-Portfolio-Unshare-And-Delete-Activity-Session"
    )


def create_client(service: str, role: str, region: str, aws_profile: str):
    """Creates a BOTO3 client using the correct target accounts Role."""
    try:
        session = boto3.session.Session(profile_name=aws_profile, region_name=region)
        creds = assume_role(role, session)
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


def remove_product_from_portfolio(
    region: str,
    portfolio_name_substring: str,
    AWS_PROFILE: str,
    API_ACCOUNT_ID: str,
    ROLE_NAME: str,
):
    """
    This methods removes the portfolio products given the portfolio name for a region

    """
    try:
        sc_client = create_client(
            "servicecatalog",
            f"arn:aws:iam::{API_ACCOUNT_ID}:role/{ROLE_NAME}",
            region,
            AWS_PROFILE,
        )

        response = sc_client.list_portfolios()
        portfolios = response.get("PortfolioDetails", [])

        for portfolio in portfolios:
            portfolio_id = portfolio.get("Id")
            portfolio_name = portfolio.get("DisplayName")
            if portfolio_name_substring in portfolio_name:
                product_search_response = sc_client.search_products_as_admin(
                    PortfolioId=portfolio_id
                )
                product_view_details = product_search_response.get(
                    "ProductViewDetails", []
                )
                for product in product_view_details:
                    product_info = product.get("ProductViewSummary", {})
                    product_id = product_info.get("ProductId")
                    logger.info(
                        f"Product to be removed { product_id } from portfolio { portfolio_name }"
                    )
                    sc_client.disassociate_product_from_portfolio(
                            PortfolioId=portfolio_id, ProductId=product_id
                        )
                    logger.info(
                        f"Product to be removed { product_id } from portfolio { portfolio_name } in region : {region}"
                    )

    except ClientError as err:
        logger.error(f"Failed to delete the portfolio:\n {err}")
        raise err


def delete_portfolio(
    region: str,
    portfolio_name_substring: str,
    AWS_PROFILE: str,
    API_ACCOUNT_ID: str,
    ROLE_NAME: str,
):
    """
    This methods deletes the portfolio given the portfolio name for a region

    """
    try:
        sc_client = create_client(
            "servicecatalog",
            f"arn:aws:iam::{API_ACCOUNT_ID}:role/{ROLE_NAME}",
            region,
            AWS_PROFILE,
        )

        response = sc_client.list_portfolios()
        portfolios = response.get("PortfolioDetails", [])

        for portfolio in portfolios:
            portfolio_id = portfolio.get("Id")
            portfolio_name = portfolio.get("DisplayName")
            if portfolio_name_substring in portfolio_name:
                delete_portfolio_response = sc_client.delete_portfolio(Id=portfolio_id)
                logger.info(
                    f"Deleted portfolio { portfolio_id } region { region } delete portfolio response  {delete_portfolio_response }"
                )

    except ClientError as err:
        logger.error(f"Failed to delete the portfolio:\n {err}")
        raise err


def unshare_portfolio(
    region: str,
    portfolio_name_substring: str,
    AWS_PROFILE: str,
    API_ACCOUNT_ID: str,
    ROLE_NAME: str,
    ORAGNIZATION_NODE_TYPE_TO_BE_UNSHARED: str,
):
    """
    This methods lists out the ou ids with which the service catalog
    portfolio is shared and unshares it with all.

    """
    try:
        sc_client = create_client(
            "servicecatalog",
            f"arn:aws:iam::{API_ACCOUNT_ID}:role/{ROLE_NAME}",
            region,
            AWS_PROFILE,
        )

        ls_pf_response = sc_client.list_portfolios()
        portfolios = ls_pf_response.get("PortfolioDetails", [])

        for portfolio in portfolios:
            portfolio_id = portfolio.get("Id")
            portfolio_name = portfolio.get("DisplayName")
            if portfolio_name_substring in portfolio_name:
                response = sc_client.list_organization_portfolio_access(
                    PortfolioId=portfolio_id,
                    OrganizationNodeType=ORAGNIZATION_NODE_TYPE_TO_BE_UNSHARED,
                )
                shared_ou_ids = response.get("OrganizationNodes", [])
                for ou in shared_ou_ids:
                    unshare_api_response = sc_client.delete_portfolio_share(
                        PortfolioId=portfolio_id, OrganizationNode=ou
                    )
                    logger.info(
                        f"Unshared portfolio {portfolio_id} with OU {ou} and unshare api response {unshare_api_response}"
                    )
                    time.sleep(5)
    except ClientError as err:
        logger.error(f"Failed to unshare the portfolio:\n {err}")
        raise err


def main():
    # Accepting CLI args
    parser = (
        argparse.ArgumentParser()
    )  # parser.add_argument("--account-type", help="The account type to be used for the account type comparison.")
    parser.add_argument(
        "--portfolio-name", help="Portfolio name to be unshared and deleted", type=str
    )
    parser.add_argument(
        "--regions",
        help="A string of comma separated regions from where we have to unshare and delete the portfolios",
        type=str,
    )
    parser.add_argument(
        "--aws-profile",
        help="Aws profile locally configured to run this script and perform the required aws api calls",
        type=str,
    )
    parser.add_argument(
        "--api-account-id",
        help="An aws api account id which hosts the shareble aws service catalog portfolis and prodcuts",
        type=str,
    )
    parser.add_argument(
        "--role-name",
        help="Aws role to be assumed to access the API account services and resources",
        type=str,
    )
    parser.add_argument(
        "--orgnization-node-type-to-be-unshared",
        help=" The orgnization node type which is associated with the portfolio shared",
        type=str,
    )
    args = parser.parse_args()

    # Assigning CLI args to internal vars
    PORTFOLIO_NAME = args.portfolio_name
    REGIONS = args.regions.split(",")
    AWS_PROFILE = args.aws_profile
    API_ACCOUNT_ID = args.api_account_id
    ROLE_NAME = args.role_name
    ORAGNIZATION_NODE_TYPE_TO_BE_UNSHARED = args.orgnization_node_type_to_be_unshared

    logger.info(
        f"Input parameters portfolio_name : { PORTFOLIO_NAME}, regions {REGIONS}, PROFILE { AWS_PROFILE }, ACCOUNT_ID { API_ACCOUNT_ID },  ROLE_NAME {ROLE_NAME}"
    )
    try:
        for region in REGIONS:
            logger.info(f"Task initiated for region { region}")
            logger.info(f"Unsharing portfolio {PORTFOLIO_NAME} for region { region}")
            unshare_portfolio(
                region=region,
                portfolio_name_substring=PORTFOLIO_NAME,
                AWS_PROFILE=AWS_PROFILE,
                API_ACCOUNT_ID=API_ACCOUNT_ID,
                ROLE_NAME=ROLE_NAME,
                ORAGNIZATION_NODE_TYPE_TO_BE_UNSHARED=ORAGNIZATION_NODE_TYPE_TO_BE_UNSHARED,
            )

            logger.info(
                f"Removing portfolio {PORTFOLIO_NAME} products for region { region}"
            )
            remove_product_from_portfolio(
                region=region,
                portfolio_name_substring=PORTFOLIO_NAME,
                AWS_PROFILE=AWS_PROFILE,
                API_ACCOUNT_ID=API_ACCOUNT_ID,
                ROLE_NAME=ROLE_NAME,
            )

            logger.info(f"Deleting portfolio {PORTFOLIO_NAME} for region { region}")
            delete_portfolio(
                region=region,
                portfolio_name_substring=PORTFOLIO_NAME,
                AWS_PROFILE=AWS_PROFILE,
                API_ACCOUNT_ID=API_ACCOUNT_ID,
                ROLE_NAME=ROLE_NAME,
            )
            logger.info(f"Task finished for region { region}")
    except Exception as e:
        logger.error("An error occured: %s", str(e))


if __name__ == "__main__":
    main()
