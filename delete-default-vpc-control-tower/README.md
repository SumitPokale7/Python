## Overview
This Script deploys the Lambda function and required roles in the specified region with which we can delete default vpcs of the accounts provided in the payload.

### Step by step CFN deployment

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # set region where Lambda function to be created
export ENVIRONMENT='<hub_environment>'      # e.g. 0001/0002/0003
export HUB_ID='<hub_id>'                    # hub account ID

3. Run script from a command line to deploy CFN stack.
```bash
./deploy-cfn.sh

### Invoke Lambda to Delete default VPCs from all regions with in a spoke.
1. Go to Lambda Fuction "INTERIM-WH-XXXX-LMB-DEFAULT-VPC-DELETION-CT" and invoke it with below payload
```
{
        "accounts": ["514815511246", "295045191403", "294057259142", "713688475317","997461664129"], # replace it with accounts list of which you want to delete the default-vpc
        "regions": ["eu-west-1", "ap-southeast-3", "ap-southeast-2"] # replace it with the regions which as default vpc that needs to be deleted.
}
```

