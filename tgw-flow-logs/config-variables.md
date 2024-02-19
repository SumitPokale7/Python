### Environment Variables for H1/H2/H3

### H1
```bash
export AWS_DEFAULT_PROFILE='WH-00H1-role_OPERATIONS'    # e.g. WH-00H1-role_OPERATIONS
export AWS_REGION='eu-west-1'        # set region where Lambda function to be created
export ENVIRONMENT='0001'            # e.g. 0001/0002/0003
export HUB_ID='423499082931'         # hub account ID
export LAMBDA_LAYER_VERSION='36'     # Lambda Layer Version
export TGW_S3_ARN='arn:aws:s3:::458479718442-tgwlog-001'

### H2

```bash
export AWS_DEFAULT_PROFILE='WH-00H2-role_OPERATIONS'    
export AWS_REGION='eu-west-1'        
export ENVIRONMENT='0002'            
export HUB_ID='550590017392'         
export LAMBDA_LAYER_VERSION='20'     
export TGW_S3_ARN='arn:aws:s3:::458479718442-tgwlog-001'

### H3

```bash
export AWS_DEFAULT_PROFILE='WH-00H3-role_OPERATIONS'    
export AWS_REGION='eu-west-1'        
export ENVIRONMENT='0003'            
export HUB_ID='550772936474'         
export LAMBDA_LAYER_VERSION='21'     
export TGW_S3_ARN='arn:aws:s3:::458479718442-tgwlog-001'