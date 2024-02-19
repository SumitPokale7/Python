# [H&S] 1406795 Remove H&S CloudTrail from all accounts: remove-cloudtrail-resources

This is a one-off script that aims to remove S3 bucket and CW log group created by the Cloudtrail stack deployed into a spoke by landingzone. This is to clean up after removing the stack from the landingzone configuration.

### Method used

* Assume SPOKE-OPERATIONS role in Hub accounts (H1, H2, H3) to list all active spoke accounts which script will assume into using CIP_MANAGER role to delete the resources.

### How to use the script
Script is run from a command line.
1. Assume SPOKE-OPERATIONS role in Hub account from a command line (Personal, H1, H2, H3)
2. Run the script (replace the required variables with respective values for the hub)
```bash
sh remove-cloudtrail-resources.sh <PROFILE_NAME> <HUB_NAME> <ResourcesRegion> <HUB_ACCOUNT_NUMBER>
```
 - PROFILE_NAME - aws profile used for the script i.e. WH-00H1-role_SPOKE-OPERATIONS
 - HUB_NAME - hub name i.e. 0001
 - ResourcesRegion - region Cloudtrail resources were deployed to by LZ i.e. eu-west-1
 - HUB_ACCOUNT_NUMBER - account number for the hub i.e. 423499082931

3. Script does the following:
  - lists all active spoke accounts in Dynamodb
  - assumes CIP_MANAGER role in each spoke account
  - removes log group created by LogReplicationCloudTrail lambda
  - removes s3 bucket used for storing the Cloudtrail logs

