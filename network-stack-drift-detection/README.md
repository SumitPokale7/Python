[H&S] 3906591 Migrate Standalone V4 accounts to web-only architecture

## Overview

This is a one-off script that aims to migrate the accounts with access to OPERATIONS role that have a network-stack present.

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
    `network_stack_drift_detection.py` should use the `OPERATIONS` role. 
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_OPERATIONS
    ```

2. Script usage

```bash
cd scripts/network-stack-drift-detection/
python3 network_stack_drift_detection.py <hub_env>
e.g. python3 network_stack_drift_detection.py WH-0001
```

### network_stack_drift_detection script performs following actions:

Checks the accounts that have access to OPERATIONS role and have NETWORK-STACK present. Proceeds to check the network-stack drift for each of the accounts and if the route tables managed by the NETWORK-STACK have the expected routes and for Connected non-web accounts it checks if the CNX routes in private and local route tables match the architecture.


