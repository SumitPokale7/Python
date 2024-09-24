from argparse import ArgumentParser
import configparser
import boto3
import datetime
import pandas as pd
import logging
import sys
import json
file_name = f"./Invoke_Cloudability_Lambda_logs{datetime.datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.log"

logging.basicConfig(
    filename=file_name,
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level="INFO",
)

logger = logging.getLogger("boto3")
logger.addHandler(logging.StreamHandler(sys.stdout))
BOTO3_CONFIG = configparser(retries={"max_attempts": 10, "mode": "adaptive"})

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-e",
        type=str,
        help="Provide hub name example: WH-0003",
        required=True,
    )
    parser.add_argument("-f", type=str, help="Excel sheet having spoke accounts details", default=None)
    args = parser.parse_args()

    HubEnv = args.e
    file_path = args.f
    function_name = "{}-LMD_SPOKE-CLOUDABILITY-Custom-Resource-Lambda".format(HubEnv)
    logger.info("Function Name: "+function_name)
    df = pd.read_excel(file_path)
    df['spoke-id'] = df['spoke-id'].astype(str)
    df['spoke-id'] = df['spoke-id'].apply(lambda x: x.zfill(12))
    for index, row in df.iterrows():
        if row["mismatch"] == "Yes":
            payload = {"account": row["spoke-id"], "region": row["region"], "account-name": row["spoke_name"], "RequestType": "Update"}
            lmd_client = boto3.client('lambda')
            response = lmd_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            logger.info("Response:")
            logger.info(response)
