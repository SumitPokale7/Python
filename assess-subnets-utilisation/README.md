# [I&E] Assess subnet(s) details in IaaS accounts

## Overview

[I&E] - This script generates a CSV report capturing details from all VPC subnet(s) in particular region for all IaaS accounts in the AWS Organization.

**Output** - The generated CSV report displays info in the following CSV format:

- Account name
- Subnet friendly name (e.g. WU2B1NET001SUBNET-DMZAZb -> DMZ)
- Subnet ID
- CIDR block
- Available IP Address Count
- Total number of IPs supported by CidrBlock

## Requirements and Dependencies

### Assume IAM Role for particular AWS Account

The AWS Account IAM role is the role that the user/service account/Lambda function assumes in order to run the program for the particular account.

How to run python script directly to AWS account using AWS Token Broker role via cli?
Here is a quick guide how to run a python/bash script locally:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default AWS profile
```
export AWS_DEFAULT_PROFILE=<role_name>, e.g. WE-A1-role_DEVOPS
```

3. Setup the “boto3 client“ for desired AWS service

4. Check your access
```
aws sts get-caller-identity 
```

### How to use the script
Script is run from a command line.
1. Install requirements
```bash
pipenv install -r requirements.txt
```

2. Set environment variable for default AWS profile for the IaaS account
```
export AWS_DEFAULT_PROFILE=<role_name>, e.g. WE-A1-role_DEVOPS
```

3. Script usage 
```bash
python assess-subnets.py  -h
```

4. Run the script for the particular IaaS account
```bash
python assess-subnets.py  --account-name <Account name> --region <Region name> --output-file <csv-file-name>.csv
```

5. Script performs following actions:
  - describes all subnets' details in particular AWS account
  - generates a list of required subnets' information as report_data
  - creates a CSV report file from user input argument
  - writes report data to created CSV report file


### Script arguments
#### Required arguments
```bash
--account-name      # Please provide the IaaS account name, e.g. WE1-A1
--region            # Please provide the AWS region
```

#### Optional arguments
```bash
--output-file        # CSV output file, defaults to filename: subnets-report.csv
```

### Linting
```bash
flake8 --count
```

## *IMPORTANT NOTE*: How to run the python script for multiple IaaS (A1, B1, U1, T1, P1, P2, P3) accounts

1. PREREQUISITES => You must first assume IAM roles for each IaaS (A1, B1, U1, T1, P1, P2, P3) accounts via AWS Token Broker. For more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. Run bash script
```bash
cd scripts/assess-subnets-utilisation/
./assess-subnets-IaaS-accounts.sh
```
3. Check the CSV 'subnets-report.csv' file for results

4. Script performs following actions:
  - iterates through array and sets an AWS default profile
  - as well as runs the python script
  - creates a CSV report file in the current directory and writes report data