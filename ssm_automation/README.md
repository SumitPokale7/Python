## Overview

This is a script aims to focus on enabling adaptive concurrency for ssm automation

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
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_SPOKE-OPERATIONS
    ```

2. Script usage

```bash
cd tools-scripts/ssm_automation/
python3 enable_adaptive_concurrency.py
```


#### Target spokes are 
Specified account types

1. Update the local env var based on the table below:
    
    | Environments | DDB_PREFIX | AWS_DEFAULT_PROFILE     |
    |--------------|:-----------|:------------------------|
    | H1           | WH-0001    | WH-00H1-role_OPERATIONS |
    | H2           | WH-0002    | WH-00H2-role_OPERATIONS |
    | H3           | WH-0003    | WH-00H3-role_OPERATIONS |
    
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS
    export DDB_PREFIX=WH-0001
    ```

3. how to execute

   in dry run mode results will be written into the CLI
   ```bash
   cd tools-scripts/ssm_automation/
   python3 enable_adaptive_concurrency.py 
   ```

   in none dry run mode results will be written into the CLI
   ```bash
   cd tools-scripts/ssm_automation/
   python3 enable_adaptive_concurrency.py --no-dry-run
   ```

4. pass --account-types-inclusive parameter to target specific account types
   ```bash
   cd scripts/service-quota/
   python3 enable_adaptive_concurrency.py --account-types-inclusive Connected
   ```