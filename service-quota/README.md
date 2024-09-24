[H&S] 2536195 Update Routes per Route table VPC service limit on all existing Connected accounts

## Overview

This is a one-off script aims to focus on requesting this limit increase for all the existing Connected accounts.

## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Set environment variable for default aws profile

For example:
```bash
export AWS_PROFILE=WH-00H1-role_SPOKE-OPERATIONS
```

### How to use the script

Script is run from a command line.

1. Update the local env var accordingly:
    Example for H3 environment:
    ```bash
    export AWS_DEFAULT_PROFILE= WH-00H3-role_SPOKE-OPERATIONS
    ```

2. Script usage

```bash
cd scripts/service-quota/
python3 service-quota-connected.py <hub_env> <connected_spoke_env_type>
e.g. python3 service-quota-connected.py 0001 NonProd
```

### Script performs following actions:

Lists the account number and region for the connected accounts which needs to be updated and lists the account number and region for the connected accounts which are already updated.

## Extension of Service Quota for #6050637

This version supports all service quota increase requests.

#### Target spokes are 
- not hub
- not security
- account type is not Unmanaged
- status is Active or Provision or Provisioning or Quarantine

1. Update the local env var based on the table below:
    
    | Environments | DDB_PREFIX | AWS_DEFAULT_PROFILE     |
    |--------------|:-----------|:------------------------|
    | H1           | WH-0001    | WH-00H1-role_OPERATIONS |
    | H2           | WH-0002    | WH-00H2-role_OPERATIONS |
    | H3           | WH-0003    | WH-00H3-role_OPERATIONS |
    
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS
    export DDB_PREFIX=WH-0001
    ```
2. pick up service code based on the table below.
    
    | service code | quota name                         | quota code | desired value | PBI     |
    |--------------|:-----------------------------------|:-----------|:--------------|---------|
    | vpc          | Routes per route table             | L-93826ACB | 100.0         | Na      |
    | iam          | Managed policies per role          | L-0DA4ABF3 | 15.0          | 6050637 |
    | ssm          | Concurrently executing Automations | L-09101E66 | 300           | 6721295 |

3. how to execute

   in dry run mode results will be written into the YYYY-MM-DD-HH-mm-ss_not_processed.csv
   ```bash
   cd scripts/service-quota/
   python3 quota_manager.py --service-code ssm --quota-code L-09101E66 --desired-value 300.0
   ```

   in none dry run mode results will be written into the YYYY-MM-DD-HH-mm-ss_processed.csv
   ```bash
   cd scripts/service-quota/
   python3 quota_manager.py --service-code iam --quota-code L-0DA4ABF3 --desired-value 15.0 --no-dry-run
   ```

4. default service region for iam service quota increase request is 'us-east-1', for other services the script usage is same but only pass the different region via '--service-region' flag. 
    ```bash
   cd scripts/service-quota/
   python3 quota_manager.py --service-code iam --quota-code L-0DA4ABF3 --desired-value 15.0 --service-region us-east-2
   ```
5. if the desired value equals to the existing value or smaller than existing value then this spoke will be skipped

6. in case TooManyRequestsException or other exceptions disrupt execution, after cooling off, use '--resumed-spoke' flag and provide last successfully processed spoke account id. The second execution will skip previous ones up to this spoke and resume the process where it was left.
   ```bash
       cd scripts/service-quota/
       python3 quota_manager.py --service-code iam --quota-code L-0DA4ABF3 --desired-value 15.0 --no-dry-run --resumed-spoke <LAST_SUCCESSFUL_SPOKE_ACCOUNT_ID>
    ```

7. reporting results: the file generated in the format of "account-id,account-type,environment-type,region,status,old_value,new_value,request-status".

   | Request-status | Description                                                   | 
   |----------------|:--------------------------------------------------------------|
   | DRY-RUN        | service quota increase would have succeeded but dry run is on |    
   | SKIPPED        | service quota is same value of the new value or bigger        |
   | APPLIED        | service quota increase succeeded                              |
   | CLIENT_ERROR   | access denied or other botocore errors, investigate           | 
   | GENERIC_ERROR  | unhandled error, investigate                                  |

8. pass --account-types-inclusive parameter to target specific account types
   ```bash
   cd scripts/service-quota/
   python3 quota_manager.py --service-code ssm --quota-code L-09101E66 --desired-value 300.0 --account-types-inclusive Connected Unmanaged
   ```