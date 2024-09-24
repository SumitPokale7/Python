## Overview

This document provides a step-by-step guide to deploying a CloudFormation (CFN) stack and invoking a Lambda function to delete a specific attribute from DynamoDB table.

### Step by Step CFN Deployment

1. **Assume the Relevant Role via Command Line Interface:**
   For more details, please refer to this guide [Onboarding / Offboarding Team Members](https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section. This step ensures you have the necessary permissions to deploy the stack.

2. **Set Environment Variables:**
   From the terminal, set the following environment variables:
   ```bash
   export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
   export AWS_REGION='eu-west-1'               # Set the region where the Lambda function will be created
   export ENVIRONMENT='<hub_environment>'      # e.g. 0001/0002/0003

3. **Run script from a command line to deploy CFN stack.**
```bash
./deploy-cfn.sh

### Invoke Lambda to Delete DynamoDB Attribute from DDB table
1. Go to Lambda Fuction "'WH-XXXX-LMD-delete-ddb-attribute'" and invoke it with below payload
```
{
    "attribute_to_remove": "connectivity-type"
}
```
