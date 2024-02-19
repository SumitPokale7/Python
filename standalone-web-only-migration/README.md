[H&S] 3906591 Migrate Standalone V4 accounts to web-only architecture

## Overview

These are one-off scripts that aim to migrate the internet-facing Standalone spokes to web-only architecture.

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
    For `standalone-web-only-migration.py`, `add-web-only-ddb-field.py`, `add-if-ddb-field.py` and `connected-2az-to-3az-migration.py` you should use the `DEVOPS` role and for `post-migration-cleanup.py`, `fw-subnets-check`, `nacl-audit`, `rt-cleanup` and `update-connected-public-nacl-rules.py` should use the `OPERATIONS` role. 
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_OPERATIONS
    ```

2. Script usage

```bash
cd scripts/standalone-web-only-migration/
python3 standalone-web-only-migration.py <hub_env> <hub_account_id>
e.g. python3 standalone-web-only-migration.py WH-0001 423499082931

python3 post-migration-cleanup.py <hub_env> <hub_account_id>
e.g. python3 post-migration-cleanup.py WH-0001 423499082931

python3 connected-2az-to-3az-migration.py <hub_env> <hub_account_id>
e.g. python3 connected-2az-to-3az-migration.py WH-0001 423499082931

python3 trigger-network-update.py <hub_env> <hub_account_id>
e.g. python3 trigger-network-update.py WH-0001 423499082931
```
For above scripts you should update the `spoke_list = []` with the list of accounts you want to migrate.
e.g. spoke_list = ["WS-Z21V", "WS-Z213"]

```bash
cd scripts/standalone-web-only-migration/
python3 add-web-only-ddb-field.py <hub_env>
e.g. python3 add-web-only-ddb-field.py WH-0001

python3 fw-subnets-check.py <hub_env>
e.g. python3 fw-subnets-check.py WH-0001

python3 nacl-audit.py <hub_env> <network_type>
e.g. python3 fw-subnets-check.py WH-0001 Standalone-4-Tier-3-AZ  

python3 add-if-ddb-field.py <hub_env>
e.g. python3 add-if-ddb-field.py WH-0001

python3 update-connected-public-nacl-rules.py <hub_env> <environment_type>
e.g. python3 update-connected-public-nacl-rules.py WH-0003 NonProd
```

```bash
python3 rt-cleanup.py <hub_env>
e.g. python3 rt-cleanup.py WH-0003
```
For the above script you should update the `transit_gateway_id_dict` with TGW IDs of the environment you're running the script against.

### standalone-web-only-migration script performs following actions:

Updates the spoke item in dynamodb with `network-web-only` field set to true and then triggers the network stack update for that spoke account.

###  post-migration-cleanup script performs following actions:

Removes the `network-firewall-enabled` tag from the spoke account VPC to trigger Firewall Manager resource deletion and then updates the Public NACL with the required rules.

The post-migration-cleanup should be triggered once confirmed that everything went well and customers didn't loose connectivity after standalone-web-only-migration script was runned to update the CFN network stack to be web-only.

###  add-web-only-ddb-field script performs following actions:

Gets the list of Connected IF accounts and Standalone accounts that are missing the network-web-only field in Dynamodb and updates it to False for that spokes

###  fw-subnets-check script performs following actions:

Gets the list of migrated Connected and Standalone accounts and check if the FW subnets were deleted successfully from them.


###  connected-2az-to-3az-migration script performs following actions:

Updates the spoke item in dynamodb with `network-type` field set to `Connected-4-Tier-3-AZ` and then triggers the network stack update for that spoke account to migrate it from 2AZ to 3AZ template.

###  add-if-ddb-field script performs following actions:

Gets the list of Connected-4-Tier-2-AZ accounts that are missing the internet-facing field in DynamoDB and updates it to False for that spokes

### nacl-audit sctipt performs following actions:
Checks the public nacl and compares rules with the architecture and returns the ones that are non-complaint with it

### rt-cleanup script performs following actions:
Removes CNX routes from Local and Private RTs from migrated web-only accounts

### update-connected-public-nacl-rules script performs following actions:
Updates the PublicNacl routes to match the current Connected-4-Tier-3-AZ architecture. In case route 400 already exist and doesn't match the expected value it duplicates it to route 401 and then proceeds to deploy route 400. In case route 200 doesn't match the architecture of Connected-4-Tier-3-AZ or Connected-4-Tier-2-AZ templates it duplicates it to 201 and then proceeds to deploy route 400 matching the Connected-4-Tier-3-AZ if it matches the architecture of Connected-4-Tier-2-AZ it replaces the 0.0.0.0/0 cidr range with the 10.0.0.0/8 range without duplicating that rule to rule 201.
