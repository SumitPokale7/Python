# [H&S] Delete default VPC for all active spokes in Osaka (ap-northeast-3) region only

## Overview

[H&S] - This script gets list of all spokes from Dynamo DB that set with a status:"Active".
Connects to each spoke via role session and deletes default VPC in Osaka (ap-northeast-3) region only

## PREREQUISITES:

### Create Lambda execution IAM Role in Hub account

The AWS Account IAM role is the role that the user/service account/Lambda function assumes in order to run the program for the particular account.

1. From the AWS console create a temporary IAM Lambda execution role called (please replace Hub name accordingly)`INTERIM-<WH-XXXX>-role_Default-Vpc-Deletion-Lambda-ap-northeast-3` for lambda function. Also, create and attach `INTERIM-<WH-XXXX>-pol_Lambda_Execution-ap-northeast-3` a temporary Lambda execution policy for the execution role. Just copy the policy config from the "Default-Vpc-Deletion-Role-Trust-Policy.json" file.

### Step by step Lambda function deployment and invocation

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-X00M-role_OPERATIONS
export AWS_REGION='eu-west-2'               # set to London region where Lambda function to be created
export HUB_NAME='<hub_name>'                # e.g. WH-X00M/WH-0001/WH-0002/WH-0003
export HUB_ID='<hub_id>'                    # hub account ID
```
3. **IMPORTANT NOTE**: Please set environment variables and update variables' values in the `create-lambda-delete_default_VPC.sh` file.
This script performs following actions:
  - creates a deployment package
  - deletes existing Lambda function
  - creates Lambda funcion
  - invokes Lambda funcion

4. Run script from a command line.
```bash
./create-lambda-delete_default_VPC.sh
```
5. Access the AWS Lambda console and check details for newly created lambda, and its CW logs.
6. Switch role to couple of different spokes that been provisioned before `1st of March 2021` and validate that default VPC been deleted in the Osaka region.

### Lamba resources clean up

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-X00M-role_OPERATIONS
export AWS_REGION='eu-west-2'               # set to London region where Lambda function is created
export HUB_NAME='<hub_name>'                # e.g. WH-X00M/WH-0001/WH-0002/WH-0003
```
3. Delete temporarily created lambda

**IMPORTANT NOTE**: Please update the environmental variable and set variables in the `delete-lambda-delete_default_VPC.sh` file. This script performs following actions:
  - deletes existing Lambda function

Then run the script from terminal:
```bash
./delete-lambda-delete_default_VPC.sh
```
4. From AWS management console delete the `INTERIM-WH-XXXX-pol_Lambda_Execution-ap-northeast-3` Lambda execution policy as well as the `INTERIM-WH-XXXX-role_Default-Vpc-Deletion-Lambda-Osaka` Lambda execution role


## *INFO*: How to develop and test lambda function from local machine to Development hub

1. Assume the relevant role via Command Line Interface
From terminal set environment variable for default AWS profile:
```bash
export AWS_DEFAULT_PROFILE='<aws_profile_name>'      # e.g. WH-X00M-<your_iam_user_name_in_hub_account>
export HUB_NAME='<dev_hub_name>'                # e.g. WH-X00M
export HUB_ID='<dev_hub_id>'                    # e.g. 111222333444
export OSAKA_REGION=ap-northeast-3
export AWS_REGION=eu-west-2
```
2. Setup a main lambda function configuration file adding the sample snippet code below. Please note that's for illustration purposes only. Replace with your Dev hub and other variable and event details that you want to run test for:
```
# Run test locally - update hub account details and other required variable(s)
if __name__ == "__main__":

    logger = logging.getLogger(__name__)
    FORMAT = "[%(name)8s()]: %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    # Define vars, replace with you hub account details
    # Event details
    event = {
      "Action": "DeleteDefaultVPC"
    }
    _context = []
    lambda_handler(event, _context)
```

2. Run python script
```bash
python src/delete-default-vpc.py
```
