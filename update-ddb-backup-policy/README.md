[H&S] 6524801: Update DDB - To enable platform backup for Federated Production accounts

## Overview

This script aims to update/Add "backup-policy" attribute to "DailyBackup_7Day_Retention" for selected spoke accounts mentioned in the excel files provided as an input.

## Requirements and Dependencies
Excel file is required containing spoke account details.
File must contain following attribute columns
- Account Name to be updated


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
    For `update-ddb-backup-policy.py` you should use the `DEVOPS` or `OPERATIONS` role. 
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_DEVOPS
    ```
3. Script usage

```bash
cd scripts/update-ddb-backup-policy/
python3 update-ddb-backup-policy.py -e <hub_env> -f <excel_file_path> to perform dry run
python3 update-ddb-backup-policy.py -e <hub_env> -f <excel_file_path> --no-dry-run to perform live changes
```

###  update-ddb-backup-policy.py script performs following actions:

Gets the list of spoke accounts from the excel file and update/Add the "backup-policy" field from DynamoDB to "DailyBackup_7Day_Retention".
