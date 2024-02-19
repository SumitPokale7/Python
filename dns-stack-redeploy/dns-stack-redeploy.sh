#!/bin/bash
#Script to delete and recreate a DNS stack in the spokes
set -e

if [[ "$#" -ne 3 ]]
then
    echo "Deployment script SH file - Missing argument!"
    echo "Usage:"
    echo "$0 <PROFILE_NAME> <HUB_NAME> <HUB_ACCOUNT_NUMBER>"
    echo "Example:"
    echo "WH-00H1-role_SPOKE-OPERATIONS 0001 423499082931"
    exit 1
fi

PROFILE_NAME="${1}"
HUB_NAME="${2}"
HUB_ACCOUNT_NUMBER="${3}"
SPOKE_ROLE="CIP_MANAGER"

################################################################################################################################
# The below fragment of code should only be used in H1 and H2. For H3 it's safer to invoke the script manually for 1-5 spokes
# at a time to have a full control on the stack deletion and recreation process as it causes a DNS downtime in prod spokes
################################################################################################################################
# spoke_list=$(aws dynamodb scan --profile "${PROFILE_NAME}" --region eu-west-1 \
#     --table-name "WH-${HUB_NAME}-DYN_METADATA" \
#     --filter-expression "#s=:status AND #r=:region AND attribute_exists(dns_version)" \
#     --expression-attribute-names '{"#s":"status", "#r":"region"}' \
#     --expression-attribute-values "{ \":status\" : { \"S\" : \"Active\" }, \":region\" : { \"S\" : \"us-east-2\" } }" | jq -r '.Items[]."account-name".S' )
# echo "List of spokes to dissasociate resolver rules: ${spoke_list}"
################################################################################################################################

# List of spokes that the deletion and recreation of the stack should be performed
spoke_list="<INSERT_SPACE_SEPARATED_LIST_OF_SPOKES_NAME>"

for spoke in $spoke_list; do
    spoke_id=$(aws dynamodb get-item --profile "${PROFILE_NAME}" --region eu-west-1 \
        --table-name "WH-${HUB_NAME}-DYN_METADATA" \
        --key '{"account-name": {"S": "'"${spoke}"'"}}' \
        --consistent-read \
        --return-consumed-capacity NONE | jq -r '.Item.account.S' )

    echo ">> Deleting DNS stack in ${spoke} (${spoke_id}) spoke account."
    aws lambda invoke --profile "${PROFILE_NAME}" \
        --region "eu-west-1" \
        --function-name "WH-${HUB_NAME}-LMD_DNS-SERVICE" \
        --invocation-type "RequestResponse" \
        --payload '{"RequestType":"Delete","ServiceToken":"'"arn:aws:lambda:eu-west-1:${HUB_ACCOUNT_NUMBER}:function:WH-${HUB_NAME}-LMD_DNS-SERVICE"'","ResponseURL":"http://pre-signed-S3-url-for-response","StackId":"FakeStackId","RequestId":"ef4adb24-6b00-4bd6-bace-2ccbab761af2","LogicalResourceId":"FakeLogicalResourceId","ResourceType":"Custom::DNSService","ResourceProperties":{"ServiceToken":"'"arn:aws:lambda:eu-west-1:${HUB_ACCOUNT_NUMBER}:function:WH-${HUB_NAME}-LMD_DNS-SERVICE"'","AccountId":"'"${spoke_id}"'","AccountName":"'"${spoke}"'"}}' \
        --cli-read-timeout 0 \
        --cli-connect-timeout 0 \
        --log-type Tail \
        --query='LogResult' \
        --output=text response_deletion.json | base64 -d | tee response_deletion.log
    echo "DNS stack deleted for spoke account: ${spoke}"

    echo ">> Creating DNS stack in ${spoke} (${spoke_id}) spoke account."
    aws lambda invoke --profile "${PROFILE_NAME}" \
        --region "eu-west-1" \
        --function-name "WH-${HUB_NAME}-LMD_DNS-SERVICE" \
        --invocation-type "RequestResponse" \
        --payload '{"RequestType":"Create","ServiceToken":"'"arn:aws:lambda:eu-west-1:${HUB_ACCOUNT_NUMBER}:function:WH-${HUB_NAME}-LMD_DNS-SERVICE"'","ResponseURL":"http://pre-signed-S3-url-for-response","StackId":"FakeStackId","RequestId":"ef4adb24-6b00-4bd6-bace-2ccbab761af2","LogicalResourceId":"FakeLogicalResourceId","ResourceType":"Custom::DNSService","ResourceProperties":{"ServiceToken":"'"arn:aws:lambda:eu-west-1:${HUB_ACCOUNT_NUMBER}:function:WH-${HUB_NAME}-LMD_DNS-SERVICE"'","AccountId":"'"${spoke_id}"'","AccountName":"'"${spoke}"'"}}' \
        --cli-read-timeout 0 \
        --cli-connect-timeout 0 \
        --log-type Tail \
        --query='LogResult' \
        --output=text response_creation.json | base64 -d | tee response_creation.log
    echo "DNS stack created for spoke account: ${spoke}"

done
