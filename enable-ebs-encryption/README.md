Bug 6986107: Calgary region AWS accounts should have EBS encryption by default set to true

## Overview

This script aims to update/enable "ebs encryption" for all the accounts(Hub and Spokes)

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
1. Set Personal Access Token
    To install hs-service
    ```bash
    export PIP_INDEX_URL=https://AWSPlatformPython:${token}@pkgs.dev.azure.com/bp-digital/AWS%20Platform/_packaging/AWSPlatformPython/pypi/simple/
    ```

2. Install requirements
```bash
pip install -r requirements.txt
```

3. Update the local env var accordingly:
    For `enable_ebs_encryption.py` you should use the `OPERATIONS` role. 
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS
    ```
3. Script usage

```bash
cd scripts/enable-ebs-encryption/
python3 enable_ebs_encryption.py -e <hub_env> to perform dry run #Hub env = WH-X008(DevHub)/WH-001(H1)/WH-002(H2)/WH-003(H3)
python3 enable_ebs_encryption.py -e <hub_env> --no-dry-run to perform live changes
```

###  enable_ebs_encryption.py script performs following actions:

Gets the list of spoke accounts from the dynamodb and enables the ebs encryption for all the accounts in the following regions.
["eu-west-2","us-east-2","ap-southeast-2","eu-central-1","ap-southeast-1","eu-west-1","ap-southeast-3","ca-west-1","us-east-1"] 
