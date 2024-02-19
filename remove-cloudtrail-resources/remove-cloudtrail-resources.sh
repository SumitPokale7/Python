#!/bin/bash
#Script to remove Cloudtrail buckets and cloudtrail retention lambda log group from spoke accounts
set -e

if [[ "$#" -ne 4 ]]
then
    echo "Deployment script SH file - Missing argument!"
    echo "Usage:"
    echo "$0 <PROFILE_NAME> <HUB_NAME> <ResourcesRegion> <HUB_ACCOUNT_NUMBER>"
    echo "Example:"
    echo "WH-00H1-role_SPOKE-OPERATIONS 0001 eu-west-1 423499082931"
    exit 1
fi

PROFILE_NAME=$1
HUB_NAME=$2
REGION=$3
HUB_ACCOUNT_NUMBER=$4
SPOKE_ROLE="CIP_MANAGER"


active_spokes=$(aws dynamodb scan --profile $PROFILE_NAME --region $REGION \
    --table-name "WH-${HUB_NAME}-DYN_METADATA" \
    --filter-expression "#s=:status" \
    --expression-attribute-names '{"#s":"status"}' \
    --expression-attribute-values "{ \":status\" : { \"S\" : \"Active\" } }" | jq -r '.Items[].account.S')

for spoke in $active_spokes; do
    if [[ $spoke = "${HUB_ACCOUNT_NUMBER}" ]]
    then
        echo "For hub account (${spoke}) go to a console and delete the bucket and log group manually."
    else
        #assuming to the spoke
        temp_role=$(aws sts assume-role \
                        --role-arn "arn:aws:iam::${spoke}:role/${SPOKE_ROLE}"\
                        --role-session-name "CTBucketDeletion"\
                        --duration-seconds 3000)
        export AWS_ACCESS_KEY_ID=$(echo ${temp_role} | jq .Credentials.AccessKeyId | xargs)
        export AWS_SECRET_ACCESS_KEY=$(echo ${temp_role} | jq .Credentials.SecretAccessKey | xargs)
        export AWS_SESSION_TOKEN=$(echo ${temp_role} | jq .Credentials.SessionToken | xargs)
        export AWS_DEFAULT_REGION="${REGION}" 

        #removing LogReplicationCloudTrail lambda log group
        log_group=$(aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/${spoke}-LMD_LogReplicationCloudTrail" | jq -r '.logGroups[].logGroupName')
        if [[ -z "$log_group" ]]
        then
            echo "Log group doesn't exist for: ${spoke}"
        else
            aws logs delete-log-group --log-group-name $log_group
            echo "Log group deleted for: ${spoke}"
        fi

        # removing cloudtrail buckets from spokes
        list_buckets=$(aws s3 ls)
        if [[ $list_buckets =~ "${spoke}-cip-logs-cloudtrail" ]]
        then
            echo "Bucket exist for: ${spoke}"
            aws s3 rb s3://${spoke}-cip-logs-cloudtrail --force
        else
            echo "Bucket was already deleted for ${spoke} account."
        fi

        unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    fi
done
