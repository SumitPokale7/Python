# [H&S] 6124581 - Create a list of all Private Hosted Zones for reverse associated with the DNS Hub accounts

## Overview

The sripts intended to identify a list of reverse DNS private hosted zones.


### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

```bash
export AWS_PROFILE=<role_name>  # eg. WH-00H3-role_OPERATIONS
```

### How to use the script
```bash
cd scripts/phz-list/
python3 phz-list.py <DNS_HUB_ACCOUNT_ID> <DNS_HUB_IRELAND_VPC_ID>
```

Script performs following actions:

1. lists all the reverse PHZs associated with an Ireland region DNS HUB VPC
2. writes the list to the CSV file
