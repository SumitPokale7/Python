import os
import lib


os.environ['AWS_PROFILE'] = '<insert_profile>'  # e.g "WH-00H3-role_DEVOPS"
hub_account_name = '<insert_hub_account_name>'  # e.g."WH-0003"

# Replace with Connected-4-Tier-2-AZ or Standalone-4-Tier-3-AZ
network_type = "Standalone-4-Tier-3-AZ"
spoke_accounts = lib.get_spoke_account_info(hub_account_name, network_type)
sg_csv_file = f"{hub_account_name}-NonWeb-{network_type}-spokes-sg_audit.csv"
nacl_csv_file = f"{hub_account_name}-NonWeb-{network_type}-spokes-nacl_audit.csv"
columns_sg_csv = ('AccountName', 'GroupName', 'GroupId', 'IpProtocol', 'Source', 'FromPort', 'ToPort')
columns_nacl_csv = ('AccountName', 'NACL Name', 'NACL Id', 'Rule Direction', 'CidrBlock', 'Protocol', 'From', 'To', 'RuleAction', 'RuleNumber')
lib.create_report_file(sg_csv_file, columns_sg_csv)
lib.create_report_file(nacl_csv_file, columns_nacl_csv)

for spoke in spoke_accounts:
    try:
        securityaudit = lib.SecurityAudit(spoke["account"], spoke["region"])
        securityaudit._security_group_check(spoke["account-name"], sg_csv_file)
        securityaudit._nacl_check(spoke["account-name"], nacl_csv_file)
    except Exception as e:
        f = open('%s-log.txt' % spoke["account-name"], 'w')
        f.write('Failed to do a security audit for - %s' % e)
        f.close()
        print(f"Failed to audit {spoke['account-name']} account.")
        print(e)
        pass
