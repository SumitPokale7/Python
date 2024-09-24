# Get Accounts witohut GW Endpoint Rotues
## Overview
This lambda outputs accounts which have gateway endpoints deployed but there are not routes pointintg to them in the route tables of local or private subnets

## Deployment 
The lambda must be deployed manually to the hub environments and give the role CIP_TESTING for execution.

## Invocation

Go to manually deployed Lambda Function and invoke it with payload of structure below:
```
{
  "account_type": "Connected",
  "environment_type": "NonProd"
}
```