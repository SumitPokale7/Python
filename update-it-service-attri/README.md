[H&S] 5513840: Align Platform account DDB it-service fields: H1, H2

## Overview

This script aims to update "it-service" attribute to "AWS Platform" for selected spoke accounts mentioned in the excel files of H1/H2/DevHub environment from {hub-env}-DYN_METADATA table of DDB.

## Requirements and Dependencies
Excel file is required containing spoke account details and new it-service value to be changed for required Hub Environment.
File must contain following attribute columns
- Account Name
- IT Service
- New IT Service

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_DEVOPS 
```

### How to use the script

Run the script from a command line.
1. Install requirements
```bash
pip install -r requirements.txt
```

2. Update the local env var accordingly:
    For `update-it-service-attri.py` you should use the `DEVOPS` or `OPERATIONS` role. 
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_DEVOPS
    ```
3. Script usage

```bash
cd scripts/update-it-service-attri/
python3 update-it-service-attri.py -e <hub_env> -f <excel_file_path> to perform dry run
python3 update-it-service-attri.py -e <hub_env> -f <excel_file_path> --no-dry-run to perform live changes
```

###  update-it-service-attri.py script performs following actions:

Gets the list of spoke accounts from the excel file depending on the hub environment H1/H2/DevHub and update the "it-service" field from DynamoDB to "New it-service" field of excel file.
