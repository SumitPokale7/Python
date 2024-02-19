[H&S] 5690214 Remove AWS LandingZone resources from H1, H2 and H3


## Overview

This is a one-off script aims to delete below langing zone resources from all active spoke accounts:
1. Delete the AWSCloudFormationStackSetExecutionRole role
2. Delete log group StackSet-AWS-Landing-Zone-IamPasswordPolicyCustomR-*

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

Script is run from a command line.

1. Update the local env var accordingly:
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_OPERATIONS
    ```
2. Update the filename in script.

3. Script usage

```bash
cd tools-scripts/landingzone-spoke-resources-removal/
python3 <file-name>.py <hub_env>
e.g. python3 lz_remove_resources.py WH-0001
```
The script removes both the LZ role and log group.
### Script performs following actions:

1. Script: `lz_remove_resources.py.py`- Creates list of all Active spokes. Assumes to each spoke and checks if the AWSCloudFormationStackSetExecutionRole role exists and StackSet-AWS-Landing-Zone-IamPasswordPolicyCustomR-* log group exists and then proceeds to delete both the role (after deleting on inline policies and removing policies attachments) and the log group.