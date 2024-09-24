# [I&E] 1905880 - Delete default VPC for all Enterprise and Shared IaaS accounts in Osaka (ap-northeast-3) region only

## Overview

The sripts intended to delete default VPC for IaaS account(s) in Osaka (ap-northeast-3) region only.

## Requirements and Dependencies

### Assume IAM Role for particular Enterprise IaaS Account

The AWS Account IAM role is the role that the user/service/account/Lambda function assumes in order to run the program for the particular account.

How to run python/bash script locally for the IaaS account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

```bash
export AWS_PROFILE=<role_name>  # eg. WE-A1-role_NETWORK-ADM
```

3. Check your session access

```bash
aws sts get-caller-identity
```

### How to use the script

Script is run from a command line.

1. Install requirements

```bash
pipenv install -r requirements.txt
```

2. Set environment variables for default aws profile and required region

```bash
export AWS_PROFILE=<iaas_account_name>-role_NETWORK-ADM  # eg. WE-A1-role_NETWORK-ADM
export AWS_REGION=ap-northeast-3
export IAAS_ACCOUNT_NAME=WU2-A1
```

3. Script usage

```bash
cd scripts/remove-default-vpc-iaas-enterprise/
python ./delete-default-vpc-iaas.py -h
```

4. Run the script for the particular 'WU2-A1' IaaS account

```bash
python delete-default-vpc-iaas.py --iaas_account_name "${IAAS_ACCOUNT_NAME}" --region "${AWS_REGION}"
```

**DRY-RUN**: in order to observe API call execution without real resource deletion action, set the parameter to `DryRun=True` for 'detach_internet_gateway' API call

Script performs following actions:

- deletes default VPC and it's dependencies in Osaka region
- default VPC dependencies:
      - describes IGW details and deletes
      - describes all subnets' details and deletes

### Script arguments

#### Required arguments

```bash
--iaas_account_name        # Please provide the IaaS account name, eg. AccountName-A1
--region                   # Please provide the Osaka region name, eg. 'ap-northeast-3'
```

### Linting

```bash
flake8 --count
```

## *IMPORTANT NOTE*: How to run the python script for multiple Enterprise IaaS accounts, eg. A1, B1, U1, T1, P1, P2, P3

## PREREQUISITES

You must first assume federated IAM role for each reqiured IaaS account via AWS Token Broker console.

a) Run the 'awsconnect' file in order to assume the IAM role for each IaaS account, eg. as below:

```bash
# define IaaS accounts to assume federated role for
IAAS_ACC_NAMES=(<list_of_iaas_accunts>)   # eg. (AccountName-A1 WU2-A1 AccountName-B1 WU2-B1 AccountName-T1 WU2-T1)
ROLE_SUFFIX="-role_NETWORK-ADM"           # federated role name
PATH_AWSCONNECT="<full_path>/awsconnect"  # awsconnect file location

# obtain session credentatials, replace <PATH_AWSCONNECT> accourdingly
echo "${IAAS_ACC_NAMES[@]}" | xargs -n1 | sed -e "s/$/${ROLE_SUFFIX}/" | sed -e 's/^/--role /' | xargs | xargs -rt -- "${PATH_AWSCONNECT}"
```

b) In your terminal browse the given URL or scan the QR code. In the AWS Token Broker console you should see all assumed role.

1. Run bash script

Script is run from a command line.

```bash
cd scripts/remove-default-vpc-iaas-enterprise/
./delete-default-vpc-IaaS.sh "$IAAS_ACC_NAMES" "$ROLE_SUFFIX"
```

**DRY-RUN**: in order to observe API call execution without real resource deletion action, set the parameter to `DryRun=True` for 'detach_internet_gateway' API call

Script performs following actions:

- iterates through array and sets an AWS default profile for each Enterprise IaaS account
- runs the python script against it
