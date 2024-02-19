[H&S] 5531512: Remove environment-type attribute from Sandbox accounts

## Overview

This script aims to remove "environment-type" attribute for Sandbox account from our DDB Table since it is no longer required.

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
    For `remove-environment-type-attribute-sandbox-acc.py` you should use the `DEVOPS` role. 
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H3-role_DEVOPS
    ```
2. Script usage

```bash
cd scripts/remove-environment-type-attribute-ddb/
python3 remove-environment-type-attribute-sandbox-acc.py <hub_env>
e.g. python3 remove-environment-type-attribute-sandbox-acc.py WH-0001
```

###  remove-environment-type-attribute-sandbox-acc.py script performs following actions:

Gets the list of Sandbox accounts and removes "environment-type" field from DynamoDB for those accounts since this feild is no longer neccesary.
