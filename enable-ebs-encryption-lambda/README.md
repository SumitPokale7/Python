## Overview
There are two scripts which is used for ebs default encryption enablement in the aws accounts.
ebs_encryption_enterprise.py - Takes in the csv file data as an input for enterprise accounts.
rest enable-ebs-encryption.py - Is the lambda to be deployed in H1/H2/H3 which enables the ebs encryption for Hub and Spoke accounts, takes in the the csv file uploaded in s3 bucket as an event.
ex. 
{
  "no_dry_run": true,
  "s3_key": "enable-ebs-encryption/account_list.csv",
  "s3_bucket": "wh-x008-cip-gitlab-ci-eu-west-1"
}
### Dependencies
csv file with following coloumns.
account-id,account-name,account-type,environment-type,role

### Step by step guide

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # set region where Lambda function to be created
export ENVIRONMENT='<hub_environment>'      # e.g. 0001/0002/0003
export HUB_ID='<hub_id>'                    # hub account ID
export BUCKET_NAME='<destination_bucket>'   # bucket the CSV file should be saved to
```
NOTE: You can see the variables in the `config-variables.md` file

3. Run script from a command line to deploy CFN stack.
```bash
./deploy-cfn.sh
```
### Invoke Lambda to enable ebs encryption in the spoke and hub accounts
4. Go to Lambda Fuction "WH-XXXX-LMD-ENABLE-EBS-ENCRYPTION" and invoke it with below example payload
```bash
{
  "no_dry_run": true,
  "s3_key": "enable-ebs-encryption/account_list.csv",
  "s3_bucket": "wh-x008-cip-gitlab-ci-eu-west-1"
}
```
pass the csv file uploaded in s3 bucket

5. For the script ebs_encryption_enterpeise.py run it locally for enterprise account with csv file path as an input and --no-dry-run for execution.