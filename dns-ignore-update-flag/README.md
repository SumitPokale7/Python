[H&S] Product Backlog Item 5752637: Redeploy Central endpoints in Ireland and Ohio for SSM and EC2

## Overview

This is a one-off script that aims to add the 'dns_ignore_update' flag to the list of accounts provided

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
    For `dns-ignore-update-flag.py` you should use the `DEVOPS` or `OPERATIONS` role. 
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_OPERATIONS
    ```

2. Script usage

```bash
cd scripts/dns-ignore-update-flag/
python3 dns-ignore-update-flag.py <hub_env> 
e.g. python3 standalone-web-only-migration.py WH-0001
```
For above script you should update the `spoke_list = []` with the list of accounts you want to add the flag to.
e.g. spoke_list = ["WS-Z21V", "WS-Z213"]