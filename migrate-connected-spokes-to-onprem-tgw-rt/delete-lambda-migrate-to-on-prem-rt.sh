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


# Catch missing environmental variable
fatal() {
    echo "Error: $*" >&2
    exit 1
}
hub_name="${HUB_NAME:=}"
test -n "${hub_name}" || fatal "hub_name is empty or not provided"


# Create a Lambda function
echo '>> deleting lambda function...'
aws lambda delete-function \
    --function-name INTERIM-${HUB_NAME}-LMB-MIGRATE-TO-ON-PREM-RT || true

