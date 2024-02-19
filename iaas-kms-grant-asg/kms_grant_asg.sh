#!/usr/bin/env bash

set -eo pipefail

create_grant() {
    local ACCOUNT_NAME="$1"
    local AWS_DEFAULT_REGION="$2"
    local KEY_ALIAS="alias/${ACCOUNT_NAME}-KMS_DefaultEncryptionKey"
    local KEY_ARN

    shift
    shift

    local TARGET_ACCOUNT_NAMES=( "$@" )

    echo "${ACCOUNT_NAME} (${AWS_DEFAULT_REGION}) - grant ${#TARGET_ACCOUNT_NAMES[@]} accounts:"


    if test "${#TARGET_ACCOUNT_NAMES[@]}" -eq 0; then
        echo >&2 "Error: no target accounts given"
        return 1
    fi

    printf -- '  - %s\n' "${TARGET_ACCOUNT_NAMES[@]}"

    KEY_ARN=$(aws kms describe-key --key-id "${KEY_ALIAS}" --query 'KeyMetadata.Arn' --output text --profile "${ACCOUNT_NAME}-role_DEVOPS")

    echo "KEY_ARN: ${KEY_ARN}"

    for TARGET_NAME in "${TARGET_ACCOUNT_NAMES[@]}"; do
        echo
        echo "granting ${TARGET_NAME} (${ACCOUNT_NAME}) ..."

        TARGET_ID=$(aws sts get-caller-identity \
            --query 'Account' \
            --output text \
            --profile "${TARGET_NAME}-role_DEVOPS")

        GRANT_ID=$(aws kms list-grants \
            --key-id "${KEY_ARN}" \
            --query="Grants[?Name=='${TARGET_NAME}_AWSServiceRoleForAutoScaling'][GrantId]" \
            --output text \
            --profile "${ACCOUNT_NAME}-role_DEVOPS")

        if test -n "${GRANT_ID}"; then
            echo "  GrantId: ${GRANT_ID} / already_granted"
            continue
        fi

        GRANT_ID=$(aws kms create-grant \
            --name "${TARGET_NAME}_AWSServiceRoleForAutoScaling" \
            --key-id "${KEY_ARN}" \
            --grantee-principal "arn:aws:iam::${TARGET_ID}:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling" \
            --operations "Encrypt" "Decrypt" "ReEncryptFrom" "ReEncryptTo" "GenerateDataKey" "GenerateDataKeyWithoutPlaintext" "DescribeKey" "CreateGrant" \
            --query 'GrantId' \
            --output text \
            --profile "${TARGET_NAME}-role_DEVOPS")

        echo "  GrantId: ${GRANT_ID} / granted"
    done

    echo
}

create_grant "WE1-A1" "eu-west-1" "WE1-A1"
create_grant "WU2-A1" "us-east-2" "WU2-A1"

create_grant "WE1-B1" "eu-west-1" "WE1-B1" "WE1-U1"
create_grant "WU2-B1" "us-east-2" "WU2-B1" "WU2-U1"

create_grant "WE1-P1" "eu-west-1" "WE1-P1" "WE1-T1" "WE1-P2" "WE1-O2" "WE1-P3" "WE1-O3"
create_grant "WU2-P1" "us-east-2" "WU2-P1" "WU2-T1" "WU2-P2" "WU2-O2" "WU2-P3" "WU2-O3"
