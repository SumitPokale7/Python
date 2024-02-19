# [H&S] 2460460 - Associate existing PHZs with the DNS Hub VPC in Sydney

## Overview

The sripts intended to associate already existing PHZs to a DNS HUB VPC deployed in a new region.

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
pipenv install -r requirements.txt
```

2. Update variables in the phz-vpc-update.py

* dns_hub_account - replace with DNS HUB account Id
* dns_hub_new_vpc_id - vpc id of a new region DNS HUB
* dns_hub_new_vpc_region - new region of a DNS HUB
* dns_hub_vpc_ireland = vpc id of ireland region DNS HUB

Example for H1 environment adding Sydney region:
```bash
dns_hub_account = "213804799719"
dns_hub_new_vpc_id = "vpc-0068b2b2d85e44c00"
dns_hub_new_vpc_region = "ap-southeast-2"
dns_hub_vpc_ireland = "vpc-074590067c7ba56b9"
```

3. Script usage

```bash
cd scripts/phz-vpc-update/
python3 phz-vpc-update.py
```

Script performs following actions:

1. lists all the PHZs associated with an Ireland region DNS HUB VPC
2. for each of the PHZ returned by the step above the script assumes to the spoke and performs below actions:
      - checks if the PHZ has already associated with a VPC of the newly added region (if yes no further actions are performed)
      - creates the VPC association authorization
      - associate the regional DNS VPC with the PHZ (this action is performed in the DNS HUB account)
      - deletes the VPC association authorization
