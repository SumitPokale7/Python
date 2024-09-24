## Overview

This script extracts information of ec2 instances

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Running on enterprise account
```bash
awsconnect --role AccountName-role_DEVOPS
```

3. Setup Default AWS Profile
```bash
export AWS_DEFAULT_PROFILE=AccountName-role_DEVOPS
```

### How to use the script

Script is run from a command line.

1. Run Python Script
```bash
python3 extract_ec2.py
```