[H&S] 3846464 Create new OUs to be managed by AWS Control Tower

## Overview

These are one-off scripts that aim to create OUs in Hub accounts.

## Requirements and Dependencies

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

Script is run from a command line.

1. Update the local env var accordingly:
    For `create_ou.py` you should use the `DEVOPS` role. 
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H3-role_DEVOPS
    ```

2. Script usage

```bash
cd scripts/create-new-ou/
python3 create_ou.py

Script Creates all OUs required for [Control Tower] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/518651976/AWS+Hub+and+Spoke+-+Organizations) 

Use additional_ou.py script for creation of any additional OUs other than baseline OUs

### create_ou.py script performs following actions:

Creates new OU mentioned in the list.
