5556824: Share the Domain join Document with all provisioned spoke accounts

## Overview

This script aims to trigger lambda function WS-XXXX-LMB_SSM-DOCUMENT-SHARING to share ssm document with current provisioned accounts.

## Requirements and Dependencies


### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_OPERATIONS
```

### How to use the script

Run the script from a command line.
1. Install requirements
```bash
pip install -r requirements.txt
```

2. Update the local env var accordingly:
    For `share-ssm-doc.py` you should use the `OPERATIONS` role. 
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS
    ```
3. Script usage

```bash
cd scripts/share-ssm-doc/
python3 share-ssm-doc.py -e <hub_env> to perform dry run
python3 share-ssm-doc.py -e <hub_env>  --no-dry-run to perform live changes
```

### share-ssm-doc.py script performs following actions:

Gets the list of current provisioned spoke accounts from the ddb DYN_METADATA table, assume AWS_PLATFORM_ADMIN role in image builder spoke account of H1/H2/H3 and trigger WS-XXXX-LMB_SSM-DOCUMENT-SHARING lambda for fetched spoke accounts. 