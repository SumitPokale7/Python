# Delete VPC Interface Endpoints

## Overview
This lambda deletes VPC interface endpoints from a list of accounts

## Deployment 
The lambda must be deployed manually to the hub environments and give the CIP_MANAGER role for execution.

## Invocation

Go to manually deployed Lambda Function and invoke it with payload of structure below:
```
{
  "accounts": [
    {
      "account_id": "123456789012",
      "region": "us-east-1",
      "endpoint_ids": [
        "vpce-1234567890abcdef0",
        "vpce-abcdef1234567890"
      ]
    },
    {
      "account_id": "987654321098",
      "region": "us-west-2",
      "endpoint_ids": [
        "vpce-0987654321abcdef",
        "vpce-fedcba0987654321"
      ]
    }
  ]
}
```