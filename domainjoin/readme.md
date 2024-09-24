## Overview

This script execute vanilla instances in different accounts.
This is created for SSM Automation testing.

The attributes can be amended based on the need

account_details.csv
ACCOUNT_NAME,ACCOUNT_ID,REGION

Include the account details which you want to execute the instances.
Note: at the moment the event rule to run ssm automation only setup in Y0T0 account in H2

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

e.g. awsconnect -r WH-00H2-role_OPERATIONS; export AWS_DEFAULT_PROFILE=WH-00H2-role_OPERATIONS
2. Edit the account_details.csv with required account to execute this script

```

### How to use the script

Script is run from a command line.

1.Setup python environment for the script

```bash
python -m venv .venv
```

2.Activate the environment

```bash
source .venv/bin/activate
```

3.Install requirements

```bash
pip install -r requirements.txt
```


4.Script usage

```bash
cd domainjoin
python domainjoin.py
```
## Normal execution to test instances uncomment below 

        initial_scenarios = [
            #  {"os_type": "RHEL", "instance_count": 1},
            # {'os_type': 'WINDOWS', 'instance_count': 1},
            # {'os_type': 'SUSE', 'instance_count': 1},
            # {'os_type': 'UBUNTU', 'instance_count': 1}
        ]
## Concurrent execution

Setup env variables

e.g.
export Account_Name="WS-Y0T0"
export Instance_Count=10

Have different terminal sessions open for each accounts e.g. WS-Y107, WS-Y0T0, WS-Y028
Setup env variables
e.g.
export Account_Name="WS-Y0T0"
export Instance_Count=10

Then execute all at once.


## Sample execution

```
sahan.perera@Sahan-Perera's-MacBook---C02DG27NML7H domainjoin % python domainjoin.py
AMI ID:ami-02c220fcee5dab581
AMI ID:ami-02c220fcee5dab581
Instance i-0adeac5fd8f4dcb41 getting created..
Instance i-0841ecfb397804fa5 getting created..
Waiting for instance i-0841ecfb397804fa5 to pass 2/2 status checks...
Waiting for instance i-0adeac5fd8f4dcb41 to pass 2/2 status checks...
Instance i-0841ecfb397804fa5 has passed 2/2 status checks.
Instance i-0841ecfb397804fa5 bootstrap skipped!
Elapsed time for i-0841ecfb397804fa5: 0:02:28.126585
Instance i-0adeac5fd8f4dcb41 has passed 2/2 status checks.
Instance i-0adeac5fd8f4dcb41 bootstrap successful!
Elapsed time for i-0adeac5fd8f4dcb41: 0:05:09.387126
```

### Notes

1. This script does not check domain join is successful or not by login to the instance.
2. Please terminate the instances which failed to bootstrapped.It's kept running for troubleshooting perposes only. Once investigate remove them manually.