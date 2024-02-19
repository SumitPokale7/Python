import sys
import pandas as pd
import logging
from argparse import ArgumentParser
from hs_service.aws.dynamodb import DynamoDB
import datetime

# Create a logger

file_name = f"./update-it-service-attri-logfile {datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"
logging.basicConfig(
    filename=file_name,
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)
logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))


def update_spoke_it_service(df, ddb_table, dry_run):
    for index, row in df.iterrows():
        if row["IT Service"] != row["New IT Service"]:

            spoke_name = row["Account Name"]
            item = ddb_table.get_spoke_details(spoke_name)
            if item is not None:
                logger.info(f"Updating for spoke account {spoke_name}")
                if not dry_run:
                    response = ddb_table.set_spoke_field(
                        spoke_name, "it-service", row["New IT Service"]
                    )
                    logger.info("Successfully Updated")
                    logger.info(response)
                else:
                    logger.info("Dry run, skipping update")
            else:
                logger.info(f"Spoke account {spoke_name} not found in DynamoDB metadata table")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-e", "--hub_env", type=str, help="Provide hub name example: WH-0002", required=True)
    parser.add_argument("-f", "--file_path", type=str, help="Provide path for excel file containing spoke accounts to be updated", required=True)
    parser.add_argument("--no-dry-run", help="Dry run", action="store_false")

    args = parser.parse_args()
    logger.info(f"Dry Run : {args.no_dry_run}")
    try:
        if args.hub_env == "WH-0003":
            logger.error("Only WH-0001/WH-0002/DevHub environments are allowed")
            exit()
        df = pd.read_excel(args.file_path)
        logger.info(f"Running for env: {args.hub_env} and reading file {args.file_path}")
        ddb_table = DynamoDB(f"{args.hub_env}-DYN_METADATA")
        logger.info(f"Updating it-service attribute for table: {args.hub_env}-DYN_METADATA")
        update_spoke_it_service(df, ddb_table, args.no_dry_run)

    except Exception as e:
        logger.error(e)
