# [H&S]This script should disassociate any spokes currently associated with the NonProd or Prod TGW
route tables and associate the TGW attachment ID with the OnPrem TGW route table. 


## Overview

[H&S] - This script gets list of all spokes from Dynamo DB that set with a status:"Active" and account-type:"Connected"".
Connects to each spoke via role session and should disassociate any spokes currently associated with the NonProd or Prod TGW
route tables and associate the TGW attachment ID with the OnPrem TGW route table.

## PREREQUISITES:

### Create Lambda execution IAM Role in Hub account

The AWS Account IAM role is the role that the user/service account/Lambda function assumes in order to run the program for the particular account.

1. From the AWS console create a temporary IAM Lambda execution role called (please replace Hub name accordingly)`INTERIM-<WH-XXXX>-role_MIGRATE-TO-ON-PREM-RT` for lambda function. Also, create and attach `INTERIM-<WH-XXXX>-pol_Lambda_MIGRATE-TO-ON-PREM-RT` a temporary Lambda execution policy for the execution role. Just copy the policy config from the "migrate-to-on-prem-trust-policy.json" file.

### Step by step Lambda function deployment and invocation

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-2'               # set to London region where Lambda function to be created
export HUB_NAME='<hub_name>'                # e.g. WH-0001/WH-0002/WH-0003
export HUB_ID='<hub_id>'                    # hub account ID

# Define environment variables to apply changes to Active, Connected & IaaS Spokes
# To migrate NonProd and Prod spokes in different regions, values for below variables can be found in another file `config-variables.md`
export ENVIRONMENT_TYPE='<environment_type>'           # set value to either NonProd or Prod, based on which spoke type to migrate 
export REGION_FOR_APPLYING_CHANGES='<spokes_region>'   # set region value to migrate Active, Connected & IaaS spokes in that region 
export TGW_PROD_RT_ID='<tgw_prod_rt_id>'               # Transit Gateway Prod Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_NON_PROD_RT_ID='<tgw_non_prod_rt_id>'       # Transit Gateway NonProd Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_ON_PREM_RT_ID='<tgw_on_prem_rt_id>'         # Transit Gateway OnPrem Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_ID='<tgw_id>'                               # Transit Gateway ID, find this in VPC -> Transit Gateway, for that region <spokes_region> 
```
3. **IMPORTANT NOTE**: Please set environment variables and update variables' values in the `create-lambda-migrate-to-on-prem-rt.sh` file.
This script performs following actions:
  - create a deployment package
  - delete existing Lambda function
  - create Lambda function
  - invoke Lambda function

4. Run script from a command line.
```bash
./create-lambda-migrate-to-on-prem-rt.sh
```
5. Access the AWS Lambda console and check details for newly created lambda, and its CW logs.
6. Switch role to couple of different spokes (Active, Connected & IaaS Prod and Non-Prod) that been provisioned and validate that TGW attachment ID is **ONLY** associated to **On-Prem Route Table**.

### Lambda resources clean up

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-2'               # set to London region where Lambda function is created
export HUB_NAME='<hub_name>'                # e.g. WH-0001/WH-0002/WH-0003
export HUB_ID='<hub_id>'                    # e.g. hub account ID

# Define environment variables to apply changes to Active, Connected & IaaS Spokes
# To migrate NonProd and Prod spokes in different regions, values for below variables can be found in another file `config-variables.md`
export ENVIRONMENT_TYPE='<environment_type>'           # set value to either NonProd or Prod, based on which spoke type to migrate 
export REGION_FOR_APPLYING_CHANGES='<spokes_region>'   # set region value to migrate Active, Connected & IaaS spokes in that region 
export TGW_PROD_RT_ID='<tgw_prod_rt_id>'               # Transit Gateway Prod Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_NON_PROD_RT_ID='<tgw_non_prod_rt_id>'       # Transit Gateway NonProd Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_ON_PREM_RT_ID='<tgw_on_prem_rt_id>'         # Transit Gateway OnPrem Route Table ID, find this in VPC-> Transit Gateway Route Tables, for that region <spokes_region>
export TGW_ID='<tgw_id>'                               # Transit Gateway ID, find this in VPC -> Transit Gateway, for that region <spokes_region> 
```
3. Delete temporarily created lambda

**IMPORTANT NOTE**: Please update the environmental variable and set variables in the `delete-lambda-delete_default_VPC.sh` file. This script performs following actions:
  - deletes existing Lambda function

Then run the script from terminal:
```bash
./delete-lambda-migrate-to-on-prem-rt.sh
```
4. From AWS management console delete the `INTERIM-<WH-XXXX>-pol_Lambda_MIGRATE-TO-ON-PREM-RT` Lambda execution policy as well as the `INTERIM-<WH-XXXX>-role_MIGRATE-TO-ON-PREM-RT` Lambda execution role
