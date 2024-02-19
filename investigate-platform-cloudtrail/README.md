# [H&S] 2540476 - Validate that AWS Platform does not deploy any Cloudtrail configuration

## Overview

The scripts intended to verify if any H&S platform deployed cloudtrail is present.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

```bash
export AWS_PROFILE=WH-00H1-role_SPOKE-OPERATIONS  # eg. WH-00H1-role_SPOKE-OPERATIONS
```

### How to use the script

Script is run from a command line.

1. Install requirements

```bash
pipenv install -r requirements.txt
```

2. Update variables in the list_cloud_trail.py

* os.environ['AWS_PROFILE'] = - pick the spoke operations role for a given hub
* hub_account_name - replace with name of the hub
* hub_account_id - replace with Hub account ID

Example for H1 environment adding Sydney region:
```bash
os.environ['AWS_PROFILE'] = "WH-00H3-role_SPOKE-OPERATIONS"
hub_account_name = "WH-0003"
```

3. Script usage

```bash
cd scripts/investigate-platform-cloudtrail/
python3 list_cloud_trail.py
```

Script performs following actions:

1. lists all Active spoke accounts
2. for each of spoke account returned by the step above the script assumes to the spoke and performs below actions:
      - lists all CloudTrails and outputs them to a csv file excluding the cloudtrail created by DS team(DS_Security_Trail_DO-NOT-MODIFY)
