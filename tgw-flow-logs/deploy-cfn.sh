
#Create Package
set -euo pipefail

SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
SELF_DIR="${SELF_FILE%/*}"
readonly SELF_FILE SELF_DIR

set -x

pushd "${SELF_DIR}" >/dev/null

echo '>> creating package...'
aws cloudformation package \
    --s3-bucket wh-${ENVIRONMENT}-cip-gitlab-ci-${AWS_REGION} \
      --s3-prefix tgw-flowlog \
      --template-file templates/transit-gateway-flowlogs.yaml \
      --output-template-file package.yaml

# Create a Lambda function
echo '>> creating lambda function and roles...'
aws cloudformation deploy \
      --template-file package.yaml \
      --stack-name WH-${ENVIRONMENT}-CFN-TRANSIT-GATEWAY-FLOWLOGS \
      --capabilities CAPABILITY_NAMED_IAM \
      --role-arn arn:aws:iam::${HUB_ID}:role/Gitlab-privileged-role_DEPLOYMENT \
      --parameter-overrides \
      AccountName=${ENVIRONMENT} \
      LambdaLayerVersion=${LAMBDA_LAYER_VERSION} \
      S3Arn=${TGW_S3_ARN} \
      --no-fail-on-empty-changeset

