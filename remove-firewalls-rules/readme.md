## Overview

This script extracts information from spoke accounts for firewall-rule-group and remove them in each account.
## Requirements

Require boto3 Version: 1.34.8
To execute in a file mode please provide a argument file in rule_arn,account,region format like this:
rslvr-frgassoc-f6dacf1c2d2540d1,651546358725,ap-northeast-2


1. Removing firewall-rule-group from spoke accounts

   - Set the env parameters:
   - HUB_NAMES="WH-00H1", 

 

```

Set to SPOKE-OPERATIONS role
enterprise_profile = f"{hub_name}-role_SPOKE-OPERATIONS"

### How to use the script

Script is run from a command line.

1. Setup python environment for the script

```bash
python -m venv .venv
```

2. Activate the environment

```bash
source .venv/bin/activate
```
3. awsconnect -r "{hub_name}-role_SPOKE-OPERATIONS"

4. Script usage

```bash
cd scripts/remove-firewalls-rules/
python remove-firewalls-rules.py
```
