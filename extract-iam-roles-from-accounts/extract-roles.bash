#!/bin/bash
accounts=( "237420445908" "762602244037" "711555459515" "907374948729" "636107724025" "019938134771" "944955582491" "835816696786" "154574199532" "334027554143")

assume-inspector () {
    echo "arn:aws:iam::"$1":role/CIP_INSPECTOR"
	OUT=$(aws sts assume-role --role-arn arn:aws:iam::"$1":role/CIP_INSPECTOR --role-session-name readonly-role --profile WH-00H3-role_READONLY)
	export AWS_ACCESS_KEY_ID=$(echo $OUT | jq -r '.Credentials''.AccessKeyId')
	export AWS_SECRET_ACCESS_KEY=$(echo $OUT | jq -r '.Credentials''.SecretAccessKey')
	export AWS_SESSION_TOKEN=$(echo $OUT | jq -r '.Credentials''.SessionToken')
	aws sts get-caller-identity
}

for acc in "${accounts[@]}"
do
    echo "$acc"
    assume-inspector $acc
    aws iam list-roles | jq -r '.Roles[].RoleName' >> "$acc".txt
done
