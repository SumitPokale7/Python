# [H&S] Override AWS Config settings for a specific accouts in order to blacklist resources

## Overview

This package will deploy resources to override Config Recorder settings in a Control Tower environment.
This deployment uses AWS SAM CLI. [Install here](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-mac.html)

### Deploy Stack resources

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members](https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # region where the stack will be created. Must be eu-west-1, default CT region
export HUB_ACCOUNT_NAME='<hub_name>'        # e.g. WH-0001/WH-0002/WH-0003
```

3. Run script from a command line.
```bash
./create-stack.sh
```

### Clean up Stack resources

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # region where the stack was deployed
export HUB_ACCOUNT_NAME='<hub_name>'        # e.g. WH-0001/WH-0002/WH-0003
```
3. Delete temporarily created lambda
Run the script from terminal:
```bash
./delete-stack.sh
```

### Note
Default parameters have been set already in the template `config_customization.yaml`
You can update them with the required values for:
1. SelectedAccounts (List of accounts to apply Config changes)
2. ConfigRecorderExcludedResourceTypes (Resources to exlude from Config recorder)
\
Also the Lambda has been setup with critical logging that can be used for alerting if required.\
Process duration is ~30 secs per account

### Sample Event Payload
#### Reset Config recorder to default
```
{
    "RequestType": "Reset",
    "account": "09876543234"    # Should be account in SELECTED accounts that has been previously modified
}
```

#### UpdateManagedAccount
```
{
   "version":"0",
   "id":"11ad2258-6668-15ed-02b4-b4a2f1697547",
   "detail-type":"AWS Service Event via CloudTrail",
   "source":"aws.controltower",
   "account":"708143388490",
   "time":"2023-08-01T10:48:15Z",
   "region":"eu-west-1",
   "resources":[

   ],
   "detail":{
      "eventVersion":"1.08",
      "userIdentity":{
         "accountId":"708143388490",
         "invokedBy":"AWS Internal"
      },
      "eventTime":"2023-08-01T10:48:15Z",
      "eventSource":"controltower.amazonaws.com",
      "eventName":"UpdateManagedAccount",
      "awsRegion":"eu-west-1",
      "sourceIPAddress":"AWS Internal",
      "userAgent":"AWS Internal",
      "requestParameters":"None",
      "responseElements":"None",
      "eventID":"27e4f51b-2168-4df8-9053-833e813e414f",
      "readOnly":false,
      "eventType":"AwsServiceEvent",
      "managementEvent":true,
      "recipientAccountId":"708143388490",
      "serviceEventDetails":{
         "updateManagedAccountStatus":{
            "organizationalUnit":{
               "organizationalUnitName":"FoundationNonProd",
               "organizationalUnitId":"ou-lhrb-6lxo8xv8"
            },
            "account":{
               "accountName":"WS-XO05",
               "accountId":"411314715538"
            },
            "state":"SUCCEEDED",
            "message":"AWS Control Tower successfully updated an enrolled account.",
            "requestedTimestamp":"2023-08-01T10:39:39+0000",
            "completedTimestamp":"2023-08-01T10:48:15+0000"
         }
      },
      "eventCategory":"Management"
   }
}
```

#### UpdateLandingZone
```
{
  "version": "0",
  "id": "398d16fb-eb6c-f327-ee76-bc61be507559",
  "detail-type": "AWS Service Event via CloudTrail",
  "source": "aws.controltower",
  "account": "708143388490",
  "time": "2023-08-02T13:05:47Z",
  "region": "eu-west-1",
  "resources": [],
  "detail": {
    "eventVersion": "1.08",
    "userIdentity": {
      "accountId": "708143388490",
      "invokedBy": "AWS Internal"
    },
    "eventTime": "2023-08-02T13:05:47Z",
    "eventSource": "controltower.amazonaws.com",
    "eventName": "UpdateLandingZone",
    "awsRegion": "eu-west-1",
    "sourceIPAddress": "AWS Internal",
    "userAgent": "AWS Internal",
    "requestParameters": "None",
    "responseElements": "None",
    "eventID": "559588bc-6fb3-4f22-b73e-04847d4294a7",
    "readOnly": false,
    "eventType": "AwsServiceEvent",
    "managementEvent": true,
    "recipientAccountId": "708143388490",
    "serviceEventDetails": {
      "updateLandingZoneStatus": {
        "rootOrganizationalUnitId": "r-lhrb",
        "organizationalUnits": [
          {
            "organizationalUnitName": "Security",
            "organizationalUnitId": "ou-lhrb-1h17vmtg"
          },
          {
            "organizationalUnitName": "SandboxPlayground",
            "organizationalUnitId": "Not Available"
          }
        ],
        "accounts": [
          {
            "accountName": "WS-XO19",
            "accountId": "751202602777"
          },
          {
            "accountName": "Master",
            "accountId": "708143388490"
          },
          {
            "accountName": "WS-XO20",
            "accountId": "918570106848"
          }
        ],
        "state": "SUCCEEDED",
        "message": "AWS Control Tower successfully updated your landing zone.",
        "requestedTimestamp": "2023-08-02T12:35:00+0000",
        "completedTimestamp": "2023-08-02T13:05:47+0000"
      }
    },
    "eventCategory": "Management"
  }
}
```