## Overview

This is a script aims to trigger the update the expiry data to $Yesterday for CE's across Enterprise with this naming convention {$CE_NAME}-DELETION-XXXX and trigger the LMD_CE_DELETION_FAN_OUT. 

## Requirements and Dependencies 
Run below command to install dependencies
 'pip install requirements.txt'

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_DEFAULT_PROFILE=WU2-A1-role_DEVOPS
```

### How to use the script

Script is run from a command line.

1. 1. Install requirements
```bash
pip install -r requirements.txt
```

2.  Update the local env var accordingly:
    Example for U2-A1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WU2-A1-role_DEVOPS
    ```

3. Script usage

By default script is going to run in dry run mode, if --dry-run=False it will run in non dry run mode

```bash
cd tools-scripts/enterprise-ce-deletion
python3 enterprise-ce-operations.py --env-names <env name> --region <region name> 
python3 enterprise-ce-operations.py --env-names <env name> --region <region name> --no-dry-run
i.e We can update env name as WU2-A1", "WE1-A1", "WU2-U1", "WE1-U1", "WU2-B1", "WE1-B1, "WE1-T1", "WU2-T1", "WE1-O2", "WE1-P2", "WU2-P2", "WE1-O3", "WU2-P3", "WE1-P3", "WU2-P1", "WE1-P1"

```here default value for region is us-east-2, [WU2 is us-east-2 and WE1 is eu-west-1]

Example:
python3 enterprise-ce-operations.py --env-names WE1-A1 --region eu-west-1
python3 enterprise-ce-operations.py --env-names WE1-A1 --region eu-west-1 --no-dry-run
```
### enterprice-ce-operation perform follwoing action:
1. List the CE's with the naming convention as "{$CE_NAME}-DELETION-XXXX"
2. Update the expiration DDB 'CLOUD-ENVIRONMENTS' to yesterday 
3. trigger the lambda function 'XX-{Env}-XXX-LMD_CE_DELETION_FAN_OUT'