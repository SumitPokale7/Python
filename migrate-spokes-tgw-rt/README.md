# [H&S] Migrate Spokes between TGW RT onprem and temp

## Overview

This lambda will move TGW attachment associations from onprem TGW RT to Splitview TGW RT/TMP TGW RT.

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
action    REQUIRED  migrate or revert.
                    migrate - to migrate accounts to tgw rt (that is passed by user as a param 'tgw_rt_name')
                    revert - to migrate accounts to onprem tgw rt

accounts  REQUIRED  List of accounts to action on
                    If not passed lambda will scan DDB for Active Connected/IaaS accounts in the region

region    OPTIONAL  region to action within.
                    If not passed will use region the lambda is deployed in

scan      OPTIONAL  (EXPERIMENTAL)
                    Boolean on whether to scan metadata table for Connected account
                    This can be used when not passing accounts list

tgw_rt_name  REQUIRED  TGW route table name. Its value for TEMP Route table would be 'TGW-RT-Temp' or for SplitView Route table is  'TGW-RT-SplitView'

delete_static_route  OPTIONAL  True
                               True - to delete static route from tgw rt (that is passed by user as a param 'tgw_rt_name_other') when 'action = migrate'
                               or to add static route from tgw rt (that is passed by user as a param 'tgw_rt_name_other') when 'action = revert'

tgw_rt_name_other  DEPENDS On  if 'delete = True' specified then TGW route table name required. Its value for INSPECTION Route table would be 'TGW-RT-Inspection'

no_dynamodb  REQUIRED  True
                       True  - to not lookup in the dynmodb for the spoke accounts and get required details from payload.
                       False - to lookup in the dynamodb for the account ids which are passed in the payload to search required details respective spoke account.
```

#### Example payload

# When need to pass account ids which are managed by DynamoDB
```json
{
  "action": "migrate",
  "accounts": ["12345678910"],
  "region": "eu-west-1",
  "tgw_rt_name": "TGW-RT-SplitView",
  "delete_static_route": true,
  "tgw_rt_name_other": "TGW-RT-Inspection",
  "no_dynamodb": false
}
```
# Below payload when need to pass all required details as manually for process for those account/s which are not managed by DynamoDB
```json
{
  "action": "migrate",
  "accounts": [
      {
      "account-id": "xxxxxxxxx",
      "TGWAttachmentID": "tgw-attach-xxxxxxx",
      "VPCCIDRID": "10.x.x.x/xx",
      "TGWID": "tgw-xxxxxxxxx",
      "TGWRoutetableID": "tgw-rtb-xxxxxxxxx"
    },
    {
      "account-id": "xxxxxxxxx",
      "TGWAttachmentID": "tgw-attach-xxxxxxx",
      "VPCCIDRID": "10.x.x.x/xx",
      "TGWID": "tgw-xxxxxxxxx",
      "TGWRoutetableID": "tgw-rtb-xxxxxxxxx"
    }
],
  "region": "eu-west-1",
  "tgw_rt_name": "TGW-RT-SplitView",
  "delete_static_route": true,
  "tgw_rt_name_other": "TGW-RT-Inspection",
  "no_dynamodb": true
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
usage: gen_accounts_batches.py [-h] [-s SIZE] [-e ENV] [-r REGION] [-n NAME] [-p PROFILE]

optional arguments:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Size of batches to generate (default: 50)
  -e ENV, --env ENV     Environment type value to use in scan (default: NonProd)
  -r REGION, --region REGION
                        Region value to use in scan (default: eu-west-1)
  -n NAME, --name NAME  Hub account name (default: WH-0003)
  -p PROFILE, --profile PROFILE
                        Hub account name (default: <YOUR CURRENT AWS_DEFAULT_PROFILE>)
```

### Example

``` bash
$ ./gen_accounts_batches.py -s 5
INFO:__main__:Creating batches of size 5 from table WH-0003-DYN_METADATA with env-type NonProd
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:__main__:Scanning over DDB table: WH-0003-DYN_METADATA
INFO:__main__:Found 358 accounts. Putting in to batches of 5
Batch: 0
["514815511246", "295045191403", "294057259142", "713688475317", "997461664129"]

Batch: 1
["234531043436", "295050559992", "149145686059", "273318560426", "762823686367"]

Batch: 2
["923203785550", "780956817989", "663036817390", "469257228654", "632271604002"]

.
.
.

Batch: 71
["822331124554", "226441949578", "933262833098"]

```