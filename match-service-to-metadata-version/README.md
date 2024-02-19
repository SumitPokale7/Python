# [H&S] Match HS service version to accounts metadata version


## Overview

This script can be used to match accounts metadata version with the specified service (RBAC, DNS, DS) version.
1. It compares the version in the Cloudformation stack of the service with the corresponding service version in an account's metadata.
2. If the versions don't match, it updates the metadata to match the service version.
3. Processed accounts are printed to console. They can be added as parameters in a subsquent execution to skip those accounts.
4. Updated accounts are outputed to a csv file (updated-accounts.csv) for reference.


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

Script is run from a command line.

1. Update the local env var accordingly:
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_DEVOPS
    ```

2. Script usage

```bash
cd scripts/match-service-to-metadata-version/
python <script>.py <environment-name>
e.g. python3 WH-0001
```

### Note
1. You can pass an optional argument (output filename) to the script.
This is especially important when running subsequent executions so as not to overwrite the previous file.
The default file name is: __updated-accounts-<datetime>.csv__

For example:
```bash
python script.py WH-0001 -o <your-preferred-file-name>
```


2. The script prints the accounts that have been processed during runtime.
You can optionally pass an argument (processed accounts) to the script to skip accounts already processed if running subsequent executions due to timeout/errors/breaks.

For example:
Initial execution:
```bash
# input
python script.py WH-0001

# ouput
Getting accounts in scope..
Total number of accounts to be processed: 2
WS-Z223 \
WS-Z27F \
DONE.
2 accounts updated
```

Subsequent execution:
```bash
# input with argument -p (or --processed_accounts)
python script.py WH-0001 -p \
WS-Z223 \
WS-Z27F \

# output
Getting accounts in scope..
Total number of accounts to be processed: 0
DONE.
0 accounts updated
```
