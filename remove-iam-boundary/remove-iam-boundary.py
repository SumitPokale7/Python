import logging
import datetime
import boto3
from pandas import DataFrame, read_csv
import distutils.util
import argparse

logging.basicConfig(
    filename=f"remove-iam-role-boundary-logfile-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")


def assume_role(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="Role-RemoveBoundary-Activity-Session"
    )


def create_client(service: str, role: str, aws_profile: str):
    """Creates a BOTO3 client using the correct target accounts Role."""
    session = boto3.session.Session(profile_name=aws_profile)
    creds = assume_role(role, session)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
    )
    return client


def get_client_if_role_assumable(
    iam_role_to_be_assumed: str,
    aws_profile: str,
    account_id: str,
    account_name: str,
    iam_role: str,
    output_file_rows: list,
):
    try:
        role_arn_to_be_assumed = (
            f"arn:aws:iam::{account_id}:role/{iam_role_to_be_assumed}"
        )
        iam_client = create_client(
            "iam",
            role_arn_to_be_assumed,
            aws_profile,
        )
        return iam_client
    except Exception as err:
        logger.error(
            f"Cannot assume the role: { iam_role_to_be_assumed }, error : {err}"
        )
        logger.info(
            f"Iam role : { iam_role } deletion skipped as the role : { iam_role_to_be_assumed } "
            f"cannot be assumed for account id : { account_id }, account name : { account_name }"
        )
        # Output role status file row dictionary for the dataframe
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role,
            "Status": "Assume role issue",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return None


def get_role_if_exist(
    iam_role: str,
    account_id: str,
    account_name: str,
    iam_client: object,
    output_file_rows: list,
):
    try:
        # Getting role information
        get_role_response = iam_client.get_role(RoleName=iam_role)
        return get_role_response
    except iam_client.exceptions.NoSuchEntityException:
        logger.info(
            f"Iam role : { iam_role } deletion skipped as the role doesn't exist for account id : "
            f"{ account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role,
            "Status": "Role doesn't exist",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return None


def remove_boundary(
    iam_client: object,
    account_id: str,
    account_name: str,
    iam_role: str,
    output_file_rows: str,
):
    try:
        # Deleting the role
        delete_role_boundary_response = iam_client.delete_role_permissions_boundary(
            RoleName=iam_role
        )
        logger.info(
            f"Removed boundary from iam role : { iam_role } for account id : { account_id }, "
            f"account name : { account_name } , remove boundary api call response :  {delete_role_boundary_response }"
        )
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role,
            "Status": "IAM boundary removed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the iam boundary removal status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return True
    except Exception as err:
        logger.info(
            f"Iam role : { iam_role } boundary removal failed with error : { err } for account id : "
            f"{ account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for iam boundary removal status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role,
            "Status": "IAM boundary removal failed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the iam boundary removal status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def write_to_output_status_file(output_file_rows: str):
    try:
        output_status_df = DataFrame(output_file_rows)
        logger.info("Writing a role status dataframe to csv a file")
        output_status_df.to_csv(
            f"role-boundary-removal-status-file-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.csv",
            index=False,
        )
        return True
    except Exception as err:
        logger.info(f"Failed to write to an output csv file : error : { err }")
        return False


def remove_iam_role_boundary(
    input_file_path: str,
    aws_profile: str,
    hub_account_id: str,
    iam_role_to_to_assumed: str,
    dry_run: int,
):
    """
    This methods removes the boundary of the IAM role listed in the input csv file
    """
    try:
        # Reading an input role file
        input_file_df = read_csv(input_file_path)
        # Creating an output dataframe for the role deletion status report
        output_file_rows = []
        for index, row in input_file_df.iterrows():
            iam_role = row["RoleName"]
            account_id = "{:012d}".format(
                row["AccountID"]
            )  # 12 digit AWS account number for leading zero issue in csv
            account_name = row["AccountName"]

            # Checking if dry_run flag is set
            if dry_run:
                logger.info(
                    f"This would have removed the boundary on the iam role : { iam_role } from : "
                    f"account id : { account_id }, account name : { account_name }"
                )
                output_row_dict = {
                    "AccountID": account_id,
                    "AccountName": account_name,
                    "RoleName": iam_role,
                    "Status": "Boundary was not removed as the dry run flag was set to true",
                }
                logger.info(
                    f"Appending a row : { output_row_dict  } to the role boundary removal status dataframe."
                )
                output_file_rows.append(output_row_dict)
                continue

            # Creating an iam client for a role to be assumed in the spoke account
            iam_client = get_client_if_role_assumable(
                iam_role_to_to_assumed,
                aws_profile,
                account_id,
                account_name,
                iam_role,
                output_file_rows,
            )

            # Continuing and updating status as the role not assumable
            if iam_client is None:
                continue

            # Getting a role information
            get_role_response = get_role_if_exist(
                iam_role,
                account_id,
                account_name,
                iam_client,
                output_file_rows,
            )

            # Continuing and updating status as the role doesn't exist in the spoke account
            if get_role_response is None:
                continue

            # Skipping if any boundary attached to the role
            if "PermissionsBoundary" in get_role_response["Role"]:
                # Deleting an iam role post removing attached policies and instance profiles if any
                remove_boundary(
                    iam_client,
                    account_id,
                    account_name,
                    iam_role,
                    output_file_rows,
                )

            else:
                logger.info(
                    f"Iam role : { iam_role } boundary removal skipped due to permission boundary not being attached : "
                    f"account id : { account_id }, account name : { account_name }"
                )
                output_row_dict = {
                    "AccountID": account_id,
                    "AccountName": account_name,
                    "RoleName": iam_role,
                    "Status": "Role does not have permission boundary attached",
                }
                logger.info(
                    f"Appending a row : { output_row_dict  } to the boundary role removal status dataframe."
                )
                output_file_rows.append(output_row_dict)
        # Writing to the output file
        write_to_output_status_file(output_file_rows)
    except Exception as err:
        logger.error(f"Failed to process the role boundary removal file:\n {err}")
        raise err


def main():
    # Accepting CLI args
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file-path", help="", type=str)
    parser.add_argument("--aws-profile", help="", type=str)
    parser.add_argument("--hub-account-id", help="", type=str)
    parser.add_argument("--iam-role-to-be-assumed", type=str)
    parser.add_argument("--dry-run", type=distutils.util.strtobool, default="true")
    args = parser.parse_args()

    # Assigning CLI args to internal vars
    input_file_path = args.input_file_path
    aws_profile = args.aws_profile
    hub_account_id = args.hub_account_id
    iam_role_to_be_assumed = args.iam_role_to_be_assumed
    dry_run = args.dry_run

    logger.info(
        f"Input parameters input_file_path : { input_file_path }, aws_profile : { aws_profile }, "
        f"hub_account_id : { hub_account_id }, iam_role_to_be_assumed : {iam_role_to_be_assumed}"
    )
    try:
        start_time = datetime.datetime.now()
        logger.info(
            f"Remove iam boundary role task initiated for file path { input_file_path }, start time : {start_time} "
        )
        remove_iam_role_boundary(
            input_file_path=input_file_path,
            aws_profile=aws_profile,
            hub_account_id=hub_account_id,
            iam_role_to_to_assumed=iam_role_to_be_assumed,
            dry_run=dry_run,
        )
        end_time = datetime.datetime.now()
        logger.info(
            f"IAM boundary removal task finished, end time : {end_time}, script execution total time : {end_time-start_time}"
        )
    except Exception as err:
        logger.error("An error occured: %s", str(err))


if __name__ == "__main__":
    main()
