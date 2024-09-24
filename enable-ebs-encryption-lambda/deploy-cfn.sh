
#Create Package
set -euo pipefail

SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
SELF_DIR="${SELF_FILE%/*}"
readonly SELF_FILE SELF_DIR

set -x

pushd "${SELF_DIR}" >/dev/null
ENVIRONMENT_LOWER=$(echo ${ENVIRONMENT}|tr '[:upper:]' '[:lower:]')

# Define the path to the CSV file
CSV_FILE_PATH="account_list4.csv"

# Upload the CSV file to the S3 bucket
echo '>> uploading CSV file to S3...'
aws s3 cp ${CSV_FILE_PATH} s3://wh-${ENVIRONMENT_LOWER}-cip-gitlab-ci-${AWS_REGION}/enable-ebs-encryption/


echo '>> creating package...'
aws cloudformation package \
    --s3-bucket wh-${ENVIRONMENT_LOWER}-cip-gitlab-ci-${AWS_REGION} \
      --s3-prefix enable-ebs-encryption \
      --template-file templates/enable-ebs-encryption.yaml \
      --output-template-file package.yaml

# Create a Lambda function
echo '>> creating lambda function and roles...'
aws cloudformation deploy \
      --template-file package.yaml \
      --stack-name WH-${ENVIRONMENT}-CFN-ENABLE-EBS-ENCRYPTION \
      --capabilities CAPABILITY_NAMED_IAM \
      --role-arn arn:aws:iam::${HUB_ID}:role/Gitlab-privileged-role_DEPLOYMENT \
      --parameter-overrides HubName=${HUB_NAME} HubID=${HUB_ID} BucketName=${BUCKET_NAME} \
      --no-fail-on-empty-changeset

