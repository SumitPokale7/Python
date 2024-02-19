# Create Gateway Endpoints

## Overview
This lambda creates gateway endpoints in active accounts where customer managed endpoints do not exist.
The deployed gateway endpoint is tagged with `"managed-by": "aws-platform-team"` and the account's DynamoDB metadata is updated with `network-{service}-gw-endpoint` field as true.

If there is an existing service gateway endpoint, no action is taken in the account nd the account's DynamoDB metadata is updated with `network-{service}-gw-endpoint` field as false.

## Deployment 
The lambda must be deployed manually to the hub environments and give the CIP_MANAGER role for execution.

## Invocation

1. Go to manually deployed Lambda Function and invoke it with payload of structure below:
```
{
  "account_type": "Connected", # Required
  "environment_type": "NonProd", # Required
  "service": "s3" # Required
  "update_ignore_accounts": true, # Optional - default to false
}
```

`update_ignore_accounts` bool is used to filter out accounts with `network-ignore-update` attribute. By default this value is set to false and therefore accounts with the `network-ignore-update` attributes will be excluded. 
