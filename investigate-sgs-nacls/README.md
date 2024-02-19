# [H&S] 5278847 - Collect information related with SGs and NACLs for Non-Web Internet Facing accounts
## Overview

The sripts intended to check inbound security group rules and inbound nacls for public and firewall nacl for NonWeb Connected and Standalone accounts.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

```bash
export AWS_PROFILE= WH-00H1-role_DEVOPS  # eg. WH-00H1-role_DEVOPS
```

### How to use the script

Script is run from a command line.

1. Install requirements

```bash
pipenv install -r requirements.txt
```

2. Update variables in the security_audit.py

* os.environ['AWS_PROFILE'] = - pick the spoke operations role for a given hub
* hub_account_name - replace with name of the hub

Example for H1 environment adding Sydney region:
```bash
os.environ['AWS_PROFILE'] = "WH-00H3-role_DEVOPS"
hub_account_name = "WH-0003"
```

3. Script usage

```bash
cd scripts/investigate-sgs-nacls/
python3 security_audit.py
```

Script performs following actions:

1. lists all Standalone-4-Tier-3-AZ or Connected-4-Tier-2-AZ NonWeb spoke accounts
2. for each of spoke account returned by the step above the script assumes to the spoke and performs below actions:
      - lists all the inbound security group rules and outputs them to a csv file
      - lists all the inbound nacl rules for a public and firewall nacls and outputs them to a csv file
