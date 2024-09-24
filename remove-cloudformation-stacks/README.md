# PBI 6418761 - Remove Cloudformation Stacks in Disabled Regions

## Overview

These scripts are designed to remove Autotagger CFN stacks in disabled AWS regions. It can easily be adapted to remove any CFN stack in any region.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

```bash
export AWS_PROFILE=<role_name>  # eg. WH-00H1-role_SPOKE-OPERATIONS
```

### How to use the script

Script is run from a command line.

1. Install requirements

```bash
pip install -r requirements.txt
```

2. Script usage

```bash
cd scripts/remove-cloudformation-stacks/
python remove-cloudformation-stacks.py
```

## Script performs following actions:

- The script retrieves a list of all accounts in the AWS organization and iterates over each account.
- For each account, it assumes a specific role (AWS_PLATFORM_ADMIN) to gain necessary permissions.
- It then iterates over a predefined list of AWS regions (DISABLED_REGIONS), and for each region, it attempts to delete a specific CloudFormation stack related to an Autotagger resource.
