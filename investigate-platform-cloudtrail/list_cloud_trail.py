import os
import lib

os.environ["AWS_PROFILE"] = "<insert_profile>"  # e.g "WH-00H3-role_SPOKE-OPERATIONS"
hub_account_name = "<insert_hub_account_name>"  # e.g."WH-0003"
hub_account_id = "<insert_hub_account_id>"  # e.g. 951603865510
Spokes_completed = 0

spoke_accounts = lib.get_spoke_account_info(hub_account_name)
cl_csv_file = f"{hub_account_name}-spokes-cloud_trail_check.csv"
columns_cl_csv = ("Account_Name", "Account_Id", "CloudTrial_Name", "Home_Region")
lib.create_report_file(cl_csv_file, columns_cl_csv)

for spoke in spoke_accounts:
    try:
        spoke_id = spoke["account"]
        if not spoke["account"] == hub_account_id:
            print(f"Getting the details for spoke ${spoke_id}")
            cl_check = lib.CloudTrial(spoke["account"])
            cl_check._cloudtrail_check(
                spoke["account-name"], spoke["account"], cl_csv_file
            )
            Spokes_completed = Spokes_completed + 1
            print(f"spokes completed:{Spokes_completed}")
    except Exception as e:
        f = open("%s-log.txt" % spoke["account-name"], "w")
        f.write("Failed to do a security audit for - %s" % e)
        f.close()
        print(f"Failed to audit {spoke['account-name']} account.")
        print(e)
        pass
