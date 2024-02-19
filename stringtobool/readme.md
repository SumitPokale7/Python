[H&S] 2558871 Update metadata table items so that attribute "internet-facing" and "networking-private-2" is a boolean - change string type to bool with parameter values from "No" to false

## Overview

This script is used to change the attribute "internet-facing" type from string to bool.
Also, it helps changing the values "No","0","off" to False


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

1. Update the local env var accordingly : Update the table name as needed 
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H1-role_DEVOPS
    ```

2. Script usage

```bash
cd scripts/stringtobool/
python3 <file-name>.py <hub_env>
e.g. python3 conversion.py 0001
```