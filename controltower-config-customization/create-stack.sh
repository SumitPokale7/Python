#!/usr/bin/env bash

# A simple script to create a deployment package, create and update Config Customizer resources using SAM
# The resources are deployed in AWS London region

################################################################################################################################
# PREREQUISITES =>
# Set HUB_ACCOUNT_NAME environment variable for the Hub to deploy resources
# export HUB_ACCOUNT_NAME=WH-00H1/WH-00H2/WH-00H3
# 1. Install SAM
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-mac.html
#
# 2. Assume IAM roles for Hub account,
# e.g. WH-<your_dev_hub_name>/WH-00H1/WH-00H2/WH-00H3 via AWS Token Broker.
#
#  Step 1. Assume the relevant role via Command Line Interface, for more details please refer to this guide
# (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members)
# in the “AWS Setup“ => “Command Line Interface“ section.
#
#  Step 2. Run the 'awsconnect' file in order to assume the IAM role for Hub account
# e.g. <path-to-awsconnect-file>/awsconnect --role <dev-hub-name>-role_OPERATIONS, e.g. <dev-hub-name> : WH-00H1/WH-00H2/WH-00H3
# export AWS_DEFAULT_PROFILE=<dev-hub-name>-role_OPERATIONS
################################################################################################################################

set -euo pipefail

SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
SELF_DIR="${SELF_FILE%/*}"
readonly SELF_FILE SELF_DIR

set -x

pushd "${SELF_DIR}" >/dev/null

# Catch missing environmental variable(s)
fatal() {
    echo "Error: $*" >&2
    exit 1
}

HUB_ACCOUNT_NAME="${HUB_ACCOUNT_NAME:=}"
test -n "${HUB_ACCOUNT_NAME}" || fatal "HUB_ACCOUNT_NAME is empty or not provided"
AWS_REGION="${AWS_REGION:=}"
test -n "${AWS_REGION}" || fatal "AWS_REGION is empty or not provided"

# Declare required variables
HUB_ACCOUNT_NAME_LOWER=`echo $HUB_ACCOUNT_NAME| tr '[:upper:]' '[:lower:]'`
STACK_NAME="${HUB_ACCOUNT_NAME}-CONFIG-CUSTOMIZER"
BASEDIR=`pwd`
DEPLOY_BUCKET="${HUB_ACCOUNT_NAME_LOWER}-sam-deployment-${AWS_REGION}"
BUCKET_PREFIX="config-customizer"

# Create a deployment bucket if it doesn't exist:
echo ">>Create s3 bucket if Not Found"
if ! aws s3api head-bucket --bucket $DEPLOY_BUCKET; then aws s3 mb s3://$DEPLOY_BUCKET --region $AWS_REGION; fi


echo ">> cleaning up existing resources for clean deployment..."

# Clean up previous build resources
echo ">> cleaning build dir.."
rm -rf build

# Create resources
echo ">> Creating build package for sam deployment..."
sam build --template ./config_customization.yaml --build-dir ./build/ConfigCustomization

echo ">> Deploying stack..."
sam deploy --template-file $BASEDIR/build/ConfigCustomization/template.yaml \
    --s3-bucket $DEPLOY_BUCKET \
    --s3-prefix $BUCKET_PREFIX \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region $AWS_REGION \
    --no-fail-on-empty-changeset

echo 'Completed.'