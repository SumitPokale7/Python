# [H&S] Migrate Spokes between TGW RT onprem and temp

## Overview

This lambda will move TGW attachment associations from onprem TGW RT to temp TGW RT.

### Step by step Lambda function deployment and invocation

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # region where Lambda function to be created
export HUB_ACCOUNT_NAME='<hub_name>'        # e.g. WH-0001/WH-0002/WH-0003
export HUB_ACCOUNT_ID='<hub_id>'            # hub account ID
```

3. Run script from a command line.
```bash
./create-lambda.sh
```
4. Login to hub account and manually trigger the lambda - ** see payload section for details **

### Payload options

```
accounts  REQUIRED  List of accounts to action on
                    If not passed lambda will scan DDB for 10 Active accounts

sns topic OPTIONAL  DS sns topic to pass payload for Config Offboarding
                    Defaults to: arn:aws:sns:eu-west-1:138543098515:seceng-infra-onboarding-installer-trigger
                    In H1/H2/H3 use arn:aws:sns:eu-west-1:333448796318:seceng-infra-onboarding-installer-trigger

scan      OPTIONAL  (EXPERIMENTAL)
                    Boolean on whether to scan metadata table for active account
                    This can be used when not passing accounts list
```

#### Example payload

```json
{
  "accounts": [
    {
      "account": "0123456789",
      "account-name": "WS-XO23"
    },
    {
      "account": "0123456789",
      "account-name": "WS-XO23"
    },
    {
      "account": "0123456789",
      "account-name": "WS-XO23"
    }
  ],
  "sns_topic": "arn:aws:sns:eu-west-1:138543098515:seceng-infra-onboarding-installer-trigger"
}
```

### Lambda resources clean up

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # region where Lambda function to be created
export HUB_ACCOUNT_NAME='<hub_name>'        # e.g. WH-0001/WH-0002/WH-0003
export HUB_ACCOUNT_ID='<hub_id>'            # hub account ID
```
3. Delete temporarily created lambda
Run the script from terminal:
```bash
./delete-lambda.sh
```

## Generate Account Batches

The python script `gen_account_batches.py` has been included to allow you to easily create account batches to use in your payloads.

``` bash
usage: gen_accounts_batches.py [-h] [-n NAME] [-p PROFILE]

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Hub account name (default: None | Required: True)
  -p PROFILE, --profile PROFILE
                        aws cli profile (default: <YOUR CURRENT AWS_DEFAULT_PROFILE>)
```

### Example

``` bash
$ ./gen_accounts_batches.py -n WH-X004
INFO:__main__:Creating batches of size 10 from table WH-0003-DYN_METADATA with env-type NonProd
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:__main__:Scanning over DDB table: WH-0003-DYN_METADATA
INFO:__main__:Found 358 accounts. Putting in to batches of 5
Batch: 0
[{"account": "609761296063", "account-name": "WS-X412", "region": "eu-west-1"}, {"account": "146518327479", "account-name": "WS-X402", "region": "eu-west-1"}, {"account": "124489256131", "account-name": "WS-X413", "region": "eu-west-1"}, {"account": "235595472080", "account-name": "WS-X415", "region": "eu-west-1"}, {"account": "126189234419", "account-name": "WS-X403", "region": "eu-west-1"}, {"account": "249272243306", "account-name": "WS-X414", "region": "eu-west-1"}, {"account": "983527333379", "account-name": "WS-X409", "region": "eu-west-1"}, {"account": "356443159338", "account-name": "WS-X401", "region": "eu-west-1"}, {"account": "814873127730", "account-name": "WS-X407", "region": "eu-west-1"}, {"account": "947776653076", "account-name": "WS-X416", "region": "eu-west-1"}]

Batch: 1
[{"account": "609761296063", "account-name": "WS-X412", "region": "eu-west-1"}, {"account": "146518327479", "account-name": "WS-X402", "region": "eu-west-1"}, {"account": "124489256131", "account-name": "WS-X413", "region": "eu-west-1"}, {"account": "235595472080", "account-name": "WS-X415", "region": "eu-west-1"}, {"account": "126189234419", "account-name": "WS-X403", "region": "eu-west-1"}, {"account": "249272243306", "account-name": "WS-X414", "region": "eu-west-1"}, {"account": "983527333379", "account-name": "WS-X409", "region": "eu-west-1"}, {"account": "356443159338", "account-name": "WS-X401", "region": "eu-west-1"}, {"account": "814873127730", "account-name": "WS-X407", "region": "eu-west-1"}, {"account": "947776653076", "account-name": "WS-X416", "region": "eu-west-1"}]

Batch: 2
[{"account": "609761296063", "account-name": "WS-X412", "region": "eu-west-1"}, {"account": "146518327479", "account-name": "WS-X402", "region": "eu-west-1"}, {"account": "124489256131", "account-name": "WS-X413", "region": "eu-west-1"}, {"account": "235595472080", "account-name": "WS-X415", "region": "eu-west-1"}, {"account": "126189234419", "account-name": "WS-X403", "region": "eu-west-1"}, {"account": "249272243306", "account-name": "WS-X414", "region": "eu-west-1"}, {"account": "983527333379", "account-name": "WS-X409", "region": "eu-west-1"}, {"account": "356443159338", "account-name": "WS-X401", "region": "eu-west-1"}, {"account": "814873127730", "account-name": "WS-X407", "region": "eu-west-1"}, {"account": "947776653076", "account-name": "WS-X416", "region": "eu-west-1"}]

.
.
.

Batch: N
[{"account": "695870011059", "account-name": "WS-X408", "region": "eu-west-1"}, {"account": "106530302254", "account-name": "WS-X404", "region": "eu-west-1"}, {"account": "999318609660", "account-name": "WS-X405", "region": "eu-west-1"}, {"account": "321560189287", "account-name": "WS-X406", "region": "eu-west-1"}]

```

### Note
This Lambda is setup to process all the accounts in the batch in the payload at any step in the migration process.
Monitor the logs for success info.
If the lambda fails/encounters an error at any step - resolve the error and re-initiate (invoke) the migration (lambda) to complete the process for the same batch (payload).