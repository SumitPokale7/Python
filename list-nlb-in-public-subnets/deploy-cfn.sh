#!/bin/bash

# Enable debugging
set -x

# Ensure the script stops on errors
set -euo pipefail

# Define the directory of the script
SELF_FILE=$(realpath "$0")
SELF_DIR=$(dirname "$SELF_FILE")
readonly SELF_FILE SELF_DIR

# Print the environment variables
echo "ENVIRONMENT: ${ENVIRONMENT}"
echo "AWS_REGION: ${AWS_REGION}"

# Change to the script directory
pushd "${SELF_DIR}" >/dev/null

# Convert ENVIRONMENT to lowercase
ENVIRONMENT_LOWER=$(echo ${ENVIRONMENT} | tr '[:upper:]' '[:lower:]')
echo "ENVIRONMENT_LOWER: ${ENVIRONMENT_LOWER}"

# Create the package
echo '>> creating package...'
aws cloudformation package \
    --s3-bucket wh-${ENVIRONMENT_LOWER}-cip-gitlab-ci-${AWS_REGION} \
    --s3-prefix list-nlb-public-subnets \
    --template-file templates/list-nlb-public-subnets.yaml \
    --output-template-file package.yaml

# Deploy the CloudFormation stack
echo '>> deploying CloudFormation stack...'
aws cloudformation deploy \
    --template-file package.yaml \
    --stack-name WH-${ENVIRONMENT}-CFN-LIST-NLB-PUBLIC-SUBNETS \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides Environment=${ENVIRONMENT} \
    --no-fail-on-empty-changeset