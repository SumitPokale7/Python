## Overview
This Script deploys the Lambda function and required roles in the specified region with which we create flowlogs for TransitGateways.

### Step by step CFN deployment

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # set region where Lambda function to be created
export ENVIRONMENT='<hub_environment>'      # e.g. 0001/0002/0003
export HUB_ID='<hub_id>'                    # hub account ID
export LAMBDA_LAYER_VERSION='<Version>'     # Lambda Layer Version
export TGW_S3_ARN='<S3_arn>'                # ARN of the destination S3 bucket

3. Run script from a command line to deploy CFN stack.
```bash
./deploy-cfn.sh

### Invoke Lambda to create TransitGateway Flowlogs
1. Go to Lambda Fuction "WH-XXXX-CFN-TRANSIT-GATEWAY-FLOWLOGS" and invoke it with below payload
```
{
        "ap-southeast-2": "tgw-0ddd09bfa814ed148", # replace it with region and TGW ID of the same 
        "eu-west-1": "tgw-0ddd09bfa814ed149"
        ]
}
```

