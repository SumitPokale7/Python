## Overview
The below script deploys a lambda function responsible for describing VPC endpoints in the spoke accounts.

### Step by step guide

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) in the “AWS Setup“ => “Command Line Interface“ section.

2. From terminal set environment variable:
```bash
export AWS_DEFAULT_PROFILE='<role_name>'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'               # set region where Lambda function to be created
export ENVIRONMENT='<hub_environment>'      # e.g. 0001/0002/0003
export HUB_ID='<hub_id>'                    # hub account ID
export BUCKET_NAME='<destination_bucket>'  # bucket the CSV file should be saved to
```
NOTE: You can see the variables in the `config-variables.md` file

3. Run script from a command line to deploy CFN stack.
```bash
./deploy-cfn.sh
```
### Invoke Lambda to describe VPC endpoint in the spokes
4. Go to Lambda Fuction "INTERIM-WH-XXXX-LMD-DESCRIBE-VPC-ENDPOINTS" and invoke it with below example payload
```bash
{
  "filtered_services": [
    "kms",
    "kms-fips",
    "kinesis-streams",
    "kinesis-firehose"
  ],
  "account_types": [
    "Standalone",
    "Connected"
  ]
}
```
Pass the endpoints you want to filter by in the filtered_services list. It will search through regional endpoints of that spoke account region i.e. com.amazonaws.eu-west-1.kms

NOTE: You can alternatively run the lambda with and empty payload - in this case it will default to Standalone and Connected account_types and return all the endpoints for them.

5. Once the lambda finishes go to the specified bucket and search for the CSV file `"{hub_account_name}-VPC-ENDPOINTS.csv"` i.e WH-0001-VPC-ENDPOINTS.csv

6. Final step is the CFN stack deletion once it's no longer required
```bash
./delete-cfn.sh
```