[H&S] 2540605 Create a list of AWS Federated accounts using AWS Load Balancers in Firewall Subnets


## Overview

This is a one-off script aims to focus on creating 3 lists:
1. List of every AWS Load Balancers deployed in the Firewall subnets per AWS Federated account
2. Create a list for all the existing ENIs deployed in the Firewall subnets per AWS Federated account.
3. EC2 instances deployed in the public subnets per account.


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
cd scripts/firewall-subnets/
python3 <file-name>.py <env-type>
e.g. python3 list-alb-firewall-subnets-eni.py NonProd or 
python3 list-alb-firewall-subnets-eni.py NonProd > list-alb-firewall-subnets-eni.txt [as output will be huge]
```

### Script performs following actions:

1. Script: `list-alb-firewall-subnets-eni.py`- Creates list of every AWS Load Balancers deployed in the Firewall subnets per AWS Federated account and creates a list for all the existing ENIs deployed in the Firewall subnets per AWS Federated account.

2. Script: `connected-ec2-public-subnet.py` - Creates a list of EC2 instances deployed in the public subnets in Connected-4-Tier-2-AZ accounts.

3. Script: `standalone-ec2-public-subnet.py` - Creates a list of EC2 instances deployed in the public subnets in all Standalone accounts.
