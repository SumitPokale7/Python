[H&S] 6469687 Create new Connected feature field in DynamoDB

## Overview

These are one-off scripts that aims to add the network-connected field to all the Active Connected accounts

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_DEVOPS
```

### How to use the script

```bash
cd scripts/add-network-connected-field/

python3 add-network-connected-field.py <hub_env>
e.g. python3 add-network-connected-field.py WH-0001
```

###  add-network-connected-field script performs following actions:

Gets the list of Active Connected accounts that are missing the network-connected field in DynamoDB and updates it to True for that spokes
