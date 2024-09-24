# Enable debugging
set -x

set -euo pipefail

SELF_FILE=$(realpath "$0")
SELF_DIR=$(dirname "$SELF_FILE")
readonly SELF_FILE SELF_DIR

echo "ENVIRONMENT: ${ENVIRONMENT}"
echo "AWS_REGION: ${AWS_REGION}"

pushd "${SELF_DIR}" >/dev/null

# Convert ENVIRONMENT to lowercase
ENVIRONMENT_LOWER=$(echo ${ENVIRONMENT} | tr '[:upper:]' '[:lower:]')
echo "ENVIRONMENT_LOWER: ${ENVIRONMENT_LOWER}"

# Create the package
echo '>> creating package...'
aws cloudformation package \
    --s3-bucket wh-${ENVIRONMENT_LOWER}-cip-gitlab-ci-${AWS_REGION} \
    --s3-prefix delete-ddb-attribute \
    --template-file templates/delete-ddb-attribute.yaml \
    --output-template-file package.yaml

# Deploy the CloudFormation stack
echo '>> deploying CloudFormation stack...'
aws cloudformation deploy \
    --template-file package.yaml \
    --stack-name WH-${ENVIRONMENT}-CFN-DELETE-DDB-ATTRIBUTE \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides Environment=${ENVIRONMENT} \
    --no-fail-on-empty-changeset