[H&S] 2536195 Update Routes per Route table VPC service limit on all existing Connected accounts

## Overview

This is a one-off script aims to focus on requesting this limit increase for all the existing Connected accounts.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_SPOKE-OPERATIONS
```

### How to use the script

Script is run from a command line.

1. Update the local env var accordingly:
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_SPOKE-OPERATIONS
    ```

2. Script usage

```bash
cd scripts/service-quota/
python3 service-quota-connected.py <hub_env> <connected_spoke_env_type>
e.g. python3 service-quota-connected.py 0001 NonProd
```

### Script performs following actions:

Lists the account number and region for the connected accounts which needs to be updated and lists the account number and region for the connected accounts which are already updated.
