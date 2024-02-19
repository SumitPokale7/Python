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


# Create a deployment package for a Lambda function (.zip file):
echo ">> cleaning build dir and copy src/ code into build..."
rm -rf build && mkdir build && cp -r ./src/* build/
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
HUB_ACCOUNT_NAME="${HUB_ACCOUNT_NAME:=}"
test -n "${HUB_ACCOUNT_NAME}" || fatal "HUB_ACCOUNT_NAME is empty or not provided"
HUB_ACCOUNT_ID="${HUB_ACCOUNT_ID:=}"
test -n "${HUB_ACCOUNT_ID}" || fatal "HUB_ACCOUNT_ID is empty or not provided"


LAMBDA_NAME="INTERIM-${HUB_ACCOUNT_NAME}-LMB-MIGRATE-TO-ON-PREM-RT"
ROLE_NAME="INTERIM-${HUB_ACCOUNT_NAME}-role_MIGRATE-TGW-RT"
ROLE_ARN="arn:aws:iam::${HUB_ACCOUNT_ID}:role/$ROLE_NAME"
POLICY_NAME="INTERIM-inline-policy"

echo ">> cleaning up existing resources for clean deployment"

# Clean up previous resources
echo '>> deleting lambda function...'
aws lambda delete-function \
    --function-name $LAMBDA_NAME || true

echo '>> deleting role policy...'
aws iam delete-role-policy \
    --role-name $ROLE_NAME \
    --policy-name $POLICY_NAME || true

echo '>> deleting role...'
aws iam delete-role \
    --role-name $ROLE_NAME || true


echo ">> Creating resources for deployment"
# Create the lambda role
echo ">> Creating lambda role"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'

echo ">> Creating lambda role policy"
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name $POLICY_NAME \
    --policy-document file://migrate-tgw-trust-policy.json

echo ">> Waiting for role to propagate"
for i in {0..4}; do echo "Waiting $((5-$i))"; sleep 1; done

# Create a Lambda function
echo '>> creating lambda function...'
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --description 'Temporary Lambda to migrate from onprem TGW RT to temp TGW RT' \
    --zip-file fileb://build/dist.zip \
    --handler migrate-spokes-tgw-rt.lambda_handler \
    --runtime python3.8 \
    --timeout 900 \
    --environment "Variables={HUB_ACCOUNT_ID=${HUB_ACCOUNT_ID},HUB_ACCOUNT_NAME=${HUB_ACCOUNT_NAME}}" \
    --role $ROLE_ARN
echo 'Completed.'
