import logging
import datetime
import boto3
import pandas as pd
import distutils.util
import argparse

logging.basicConfig(
    filename=f"delete-iam-role-logfile-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger("urbanGUI")


def assume_role(role: str, session: boto3.session.Session):
    sts_client = session.client("sts")
    return sts_client.assume_role(
        RoleArn=role, RoleSessionName="Role-Delete-Activity-Session"
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
    iam_role_to_be_deleted: str,
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
            f"Iam role : { iam_role_to_be_deleted } deletion skipped as the role : { iam_role_to_be_assumed } "
            f"cannot be assumed for account id : { account_id }, account name : { account_name }"
        )
        # Output role status file row dictionary for the dataframe
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Assume role issue",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def get_role_if_exist(
    iam_role_to_be_deleted: str,
    account_id: str,
    account_name: str,
    iam_client: object,
    output_file_rows: list,
):
    try:
        # Getting role information
        get_role_response = iam_client.get_role(RoleName=iam_role_to_be_deleted)
        return get_role_response
    except iam_client.exceptions.NoSuchEntityException:
        logger.info(
            f"Iam role : { iam_role_to_be_deleted } deletion skipped as the role doesn't exist for account id : "
            f"{ account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role doesn't exist",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def detach_managed_policy(
    managed_policy: dict,
    iam_client: object,
    account_id: str,
    account_name: str,
    iam_role_to_be_deleted: str,
    output_file_rows: list,
):
    try:
        managed_policy_arn = managed_policy["PolicyArn"]
        # Detaching managed policies from the role
        detach_managed_policy = iam_client.detach_role_policy(
            RoleName=iam_role_to_be_deleted, PolicyArn=managed_policy_arn
        )
        logger.info(
            f"Managed policy : {managed_policy_arn} detached for the iam role : { iam_role_to_be_deleted } for account id : { account_id }, "
            f"account name : { account_name }, detach managed policy api response : {detach_managed_policy}"
        )
        return True
    except Exception as err:
        logger.info(
            f"Iam role : { iam_role_to_be_deleted } deletion skipped as the managed policy : { managed_policy_arn } detachment failed with error : { err } "
            f"for account id : { account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role deletion failed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def delete_inline_policy(
    inline_policy_name: dict,
    iam_client: object,
    account_id: str,
    account_name: str,
    iam_role_to_be_deleted: str,
    output_file_rows: list,
):
    try:
        # Deleting inline policies from the role
        delete_inline_policy = iam_client.delete_role_policy(
            RoleName=iam_role_to_be_deleted, PolicyName=inline_policy_name
        )
        logger.info(
            f"Inline policy : {inline_policy_name} deleted for the iam role : { iam_role_to_be_deleted } for account id : { account_id }, "
            f"account name : { account_name }, delete inline policy api response : {delete_inline_policy}"
        )
        return True
    except Exception as err:
        logger.info(
            f"Iam role : { iam_role_to_be_deleted } deletion skipped as the inline policy : {inline_policy_name} deletion failed with error : { err } "
            f"for account id : { account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role deletion failed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def remove_instance_profile(
    instance_profile: dict,
    iam_client: object,
    account_id: str,
    account_name: str,
    iam_role_to_be_deleted: str,
    output_file_rows: list,
):
    try:
        instance_profile_name = instance_profile["InstanceProfileName"]
        # Removing the role from the instance profile
        remove_instance_profiles = iam_client.remove_role_from_instance_profile(
            InstanceProfileName=instance_profile_name,
            RoleName=iam_role_to_be_deleted,
        )
        logger.info(
            f"Instance profile : {instance_profile_name} removed for the iam role : { iam_role_to_be_deleted } for account id { account_id }, "
            f"account name : { account_name }, remove instance profile api response : { remove_instance_profiles }"
        )
        return True
    except Exception as err:
        logger.info(
            f"Iam role : { iam_role_to_be_deleted } deletion failed as the instance profile removal failed with error : { err } for account id :"
            f"{ account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role deletion failed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def delete_iam_role(
    iam_client: object,
    account_id: str,
    account_name: str,
    iam_role_to_be_deleted: str,
    output_file_rows: str,
):
    try:
        # Deleting the role
        delete_role_response = iam_client.delete_role(RoleName=iam_role_to_be_deleted)
        logger.info(
            f"Deleted iam role : { iam_role_to_be_deleted } for account id : { account_id }, "
            f"account name : { account_name } , delete role api call response :  {delete_role_response }"
        )
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role deleted",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return True
    except Exception as err:
        logger.info(
            f"Iam role : { iam_role_to_be_deleted } deletion failed with error : { err } for account id : "
            f"{ account_id }, account name : { account_name }"
        )
        # Creating a row  and appending to a row list for role deletion status
        output_row_dict = {
            "AccountID": account_id,
            "AccountName": account_name,
            "RoleName": iam_role_to_be_deleted,
            "Status": "Role deletion failed",
        }
        logger.info(
            f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
        )
        output_file_rows.append(output_row_dict)
        return False


def write_to_output_status_file(output_file_rows: str):
    try:
        output_status_df = pd.DataFrame(output_file_rows)
        logger.info("Writing a role status dataframe to csv a file")
        output_status_df.to_csv(
            f"role-deletion-status-file-{datetime.datetime.now().strftime('%d-%m-%y-%H-%M-%S')}.csv",
            index=False,
        )
        return True
    except Exception as err:
        logger.info(f"Failed to write to an output csv file : error : { err }")
        return False


def role_deletion_process(
    input_file_path: str,
    aws_profile: str,
    hub_account_id: str,
    iam_role_to_to_assumed: str,
    dry_run: int,
):
    """
    This methods deletes the IAM role listed in the input csv file
    """
    try:
        # Reading an input role file
        input_file_df = pd.read_csv(input_file_path)
        # Creating an output dataframe for the role deletion status report
        output_file_rows = []
        for index, row in input_file_df.iterrows():
            iam_role_to_be_deleted = row["RoleName"]
            account_id = "{:012d}".format(
                row["AccountID"]
            )  # 12 digit AWS account number for leading zero issue in csv
            account_name = row["AccountName"]

            # Checking if dry_run flag is set
            if dry_run:
                logger.info(
                    f"This could have deleted the iam role : { iam_role_to_be_deleted } from : "
                    f"account id : { account_id }, account name : { account_name }"
                )
                output_row_dict = {
                    "AccountID": account_id,
                    "AccountName": account_name,
                    "RoleName": iam_role_to_be_deleted,
                    "Status": "Role was not deleted as the dry run flag was set to true",
                }
                logger.info(
                    f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
                )
                output_file_rows.append(output_row_dict)
                continue

            # Creating an iam client for a role to be assumed in the spoke account
            iam_client = get_client_if_role_assumable(
                iam_role_to_to_assumed,
                aws_profile,
                account_id,
                account_name,
                iam_role_to_be_deleted,
                output_file_rows,
            )

            # Continuing and updating status as the role not assumable to delete a role in the spoke account
            if iam_client is False:
                continue

            # Getting a role information
            get_role_response = get_role_if_exist(
                iam_role_to_be_deleted,
                account_id,
                account_name,
                iam_client,
                output_file_rows,
            )

            # Continuing and updating status as the role to be deleted doesn't exist in the spoke account
            if get_role_response is False:
                continue

            """
            As per AWS docs-
            Unlike the Amazon Web Services Management Console,
            when you delete a role programmatically,
            you must delete the items attached to the role manually, or the deletion fails
            So we would delete any inline policies,detach managed policies and
            remove role form a istance profile if any.
            """

            # Skipping if any boundary attached to the role
            if "PermissionsBoundary" not in get_role_response["Role"]:
                # Checking if any managed policies attached to the role
                managed_policy_list = iam_client.list_attached_role_policies(
                    RoleName=iam_role_to_be_deleted
                )
                # Iterating through the attached managed policies to the role and detaching the managed policies
                managed_policy_detachment_failure = False
                for managed_policy in managed_policy_list.get("AttachedPolicies", []):
                    managed_policy_detachment_response = detach_managed_policy(
                        managed_policy,
                        iam_client,
                        account_id,
                        account_name,
                        iam_role_to_be_deleted,
                        output_file_rows,
                    )
                    # Checking if any managed policy detachment failed and marking role deletion as failed
                    if managed_policy_detachment_response is False:
                        managed_policy_detachment_failure = True
                        break
                # Continuing to the next role as the current role marked as failed due to a managed policy detachment issue
                if managed_policy_detachment_failure is True:
                    continue

                # Checking if any inline policies attached to the role
                inline_policy_list = iam_client.list_role_policies(
                    RoleName=iam_role_to_be_deleted
                )

                # Iterating through the inline policies attached to the role and deleting the inline policies
                inline_policy_deletion_failure = False
                for inline_policy_name in inline_policy_list.get("PolicyNames", []):
                    inline_policy_deletion_response = delete_inline_policy(
                        inline_policy_name,
                        iam_client,
                        account_id,
                        account_name,
                        iam_role_to_be_deleted,
                        output_file_rows,
                    )
                    # Checking if any inline policy deletion failed and marking role deletion as failed
                    if inline_policy_deletion_response is False:
                        inline_policy_deletion_failure = True
                        break
                # Continuing to the next role as the current role marked as failed due to a inline policy delition issue
                if inline_policy_deletion_failure is True:
                    continue

                # A list of principals - to check if it's an EC2 role
                list_of_principals = [
                    statement["Principal"]["Service"]
                    for statement in get_role_response["Role"][
                        "AssumeRolePolicyDocument"
                    ]["Statement"]
                ]
                # Check for instance profiles associated with the role and remove them
                if "ec2.amazonaws.com" in list_of_principals:
                    # Listing instance profile attached to the role
                    list_instance_profiles = iam_client.list_instance_profiles_for_role(
                        RoleName=iam_role_to_be_deleted
                    )
                    # Iterating through each instance profile and removing from the role
                    instance_profile_removal_failure = False
                    for instance_profile in list_instance_profiles["InstanceProfiles"]:
                        instance_profile_removal_response = remove_instance_profile(
                            instance_profile,
                            iam_client,
                            account_id,
                            account_name,
                            iam_role_to_be_deleted,
                            output_file_rows,
                        )
                        # Checking if any instance profile removal failed and marking role deletion as failed
                        if instance_profile_removal_response is False:
                            instance_profile_removal_failure = True
                            break
                # Continuing to the next role as the current role marked as failed due to a instance profile removal issue
                if instance_profile_removal_failure is True:
                    continue

                # Deleting an iam role post removing attached policies and instance profiles if any
                delete_iam_role(
                    iam_client,
                    account_id,
                    account_name,
                    iam_role_to_be_deleted,
                    output_file_rows,
                )

            else:
                logger.info(
                    f"Iam role : { iam_role_to_be_deleted } deletion skipped due to permission boundary attached : "
                    f"account id : { account_id }, account name : { account_name }"
                )
                output_row_dict = {
                    "AccountID": account_id,
                    "AccountName": account_name,
                    "RoleName": iam_role_to_be_deleted,
                    "Status": "Role has permission boundary attached",
                }
                logger.info(
                    f"Appending a row : { output_row_dict  } to the role deletion status dataframe."
                )
                output_file_rows.append(output_row_dict)
        # Writing to the output file
        write_to_output_status_file(output_file_rows)
    except Exception as err:
        logger.error(f"Failed to process the role deletion file:\n {err}")
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
            f"Role deletion task initiated for file path { input_file_path }, start time : {start_time} "
        )
        role_deletion_process(
            input_file_path=input_file_path,
            aws_profile=aws_profile,
            hub_account_id=hub_account_id,
            iam_role_to_to_assumed=iam_role_to_be_assumed,
            dry_run=dry_run,
        )
        end_time = datetime.datetime.now()
        logger.info(
            f"Role deletion task finished, end time : {end_time}, script execution total time : {end_time-start_time}"
        )
    except Exception as err:
        logger.error("An error occured: %s", str(err))


if __name__ == "__main__":
    main()
