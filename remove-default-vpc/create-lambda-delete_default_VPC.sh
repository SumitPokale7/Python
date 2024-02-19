#!/usr/bin/env bash

# A simple script to create a deployment package, create and update Lambda funcion, and finally invoke it in London region

set -euo pipefail

SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
SELF_DIR="${SELF_FILE%/*}"
readonly SELF_FILE SELF_DIR

set -x

pushd "${SELF_DIR}" >/dev/null

################################################################################################################################
# PREREQUISITES => You must first assume IAM roles for Hub account,
# e.g. WH-<your_dev_hub_name>/WH-00H1/WH-00H2/WH-00H3 via AWS Token Broker.
#
#  Step 1. Assume the relevant role via Command Line Interface, for more details please refer to this guide
# (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members)
# in the “AWS Setup“ => “Command Line Interface“ section.
#
#  Step 2. Run the 'awsconnect' file in order to assume the IAM role for Hub account
# e.g. <path-to-awsconnect-file>/awsconnect --role <account_name-role_OPERATIONS, e.g. <dev-hub>/WH-00H1/WH-00H2/WH-00H3
################################################################################################################################


# Define variables
OSAKA_REGION='ap-northeast-3'        # region where default VPC being deleted


# Create a deployment package for a Lambda function (.zip file):
echo ">> cleaning build dir and copy src/ code into build..."
rm -rf build && mkdir build && cp -r ./src/*.py build/
echo ">> creating archive (.zip)..."
pushd build/
zip -r9qy -b /tmp dist.zip .
echo 'Done.'
popd

# Catch missing environmental variable(s)
fatal() {
    echo "Error: $*" >&2
    exit 1
}
hub_name="${HUB_NAME:=}"
test -n "${hub_name}" || fatal "hub_name is empty or not provided"
hub_id="${HUB_ID:=}"
test -n "${hub_id}" || fatal "hub_id is empty or not provided"


# Create a Lambda function
echo '>> deleting lambda function...'
aws lambda delete-function \
    --function-name INTERIM-${HUB_NAME}-LMB-DEFAULT-VPC-DELETION > /dev/null || true

# Create a Lambda function
echo '>> creating lambda function...'
aws lambda create-function \
    --function-name INTERIM-${HUB_NAME}-LMB-DEFAULT-VPC-DELETION \
    --description 'Temporary Lambda to access all active spokes in Hub and delete default VPC in Osaka region as part PBI-1905840' \
    --zip-file fileb://build/dist.zip \
    --handler delete-default-vpc.lambda_handler \
    --runtime python3.8 \
    --timeout 900 \
    --environment "Variables={HUB_ID=${HUB_ID},HUB_NAME=${HUB_NAME},OSAKA_REGION=${OSAKA_REGION}}" \
    --role arn:aws:iam::${HUB_ID}:role/INTERIM-${HUB_NAME}-role_Default-Vpc-Deletion-Lambda-ap-northeast-3  > /dev/null
echo 'Completed.'


# Invoke lambda function
echo '>> invoking lambda function'
aws lambda invoke \
    --region $AWS_REGION \
    --function-name INTERIM-${HUB_NAME}-LMB-DEFAULT-VPC-DELETION \
    --cli-binary-format raw-in-base64-out \
    --invocation-type RequestResponse \
    --payload '{"Action": "DeleteDefaultVPC"}' \
    --cli-read-timeout 0 \
    --cli-connect-timeout 0 \
    --log-type Tail \
    --query='LogResult' \
    --output=text response.json | base64 -d | tee response.log

cat response.json
