[H&S] 2550040 Copy TGW Routes from one TGW RT to another

## Overview

This is a one-off script that copies TGW Routes from one TGW RT to another.

**TGW RTs MUST be in the same account and region.**

In current configuration this will **ONLY** copy static VPC routes. 
Update the filter if you require a different set of routes.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_OPERATIONS
export AWS_DEFAULT_REGION=eu-west-1
```

### How to use the script

Script is run from a command line.

1. Update the local env var accordingly:
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H3-role_OPERATIONS
    export AWS_DEFAULT_REGION=eu-west-1
    ```

2. Script usage
See help option of script

```bash
cd scripts/copy-tgw-routes/
python3 copy-tgw-routes.py --help 
```

Example:

```bash
python3 copy-tgw-routes.py -m <TGW_RT_ID_1> -t <TGW_RT_ID_2>
```

### Script performs following actions:

Copies all routes from the given "master" Transit Gateway Route Table ID to the "target" Transit Gateway Route Table ID.