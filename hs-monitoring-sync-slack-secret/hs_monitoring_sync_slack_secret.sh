#!/usr/bin/env bash
#
#/ Sync monitoring SlackWebHook secret value from <MAIN_REGION> to supported regions within an account
#/
#/ Usage: <SELF_NAME> [-h|--help]
#

set -eu -o pipefail -o errtrace -o functrace
test "${BASH_VERSINFO[0]}" -lt 4 || shopt -s inherit_errexit nullglob compat"${BASH_COMPAT=42}"

# === configuration === #

MAIN_REGION=eu-west-1

REST_REGIONS=(
    ap-northeast-2
    ap-south-1
    ap-southeast-1
    ap-southeast-2
    eu-central-1
    eu-north-1
    eu-west-2
    eu-west-3
    us-east-1
    us-east-2
    us-west-2
)

# === bootstrap === #

: "${DEBUG:=}"
: "${FORCE:=}"
readonly DEBUG FORCE

IS_SOURCED=$(test "${BASH_SOURCE[0]}" == "${0}" || echo 1)
SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
WORK_DIR=$(\pwd -P)
DEBUG_FILE="${WORK_DIR}/${SELF_FILE##*/}.dbg"
readonly IS_SOURCED SELF_FILE WORK_DIR DEBUG_FILE

# === commands === #

usage() {
    \grep '^#/' "${SELF_FILE}" \
        | \cut -c4- \
        | \sed -e "s/<SELF_NAME>/${SELF_FILE##*/}/" -e "s/<MAIN_REGION>/${MAIN_REGION}/"
    exit 0
}

check_requirements() {
    printf '4.1\n%s\n' "${BASH_VERSION}" | \sort -CV || fatal "bash 4.1+ is required, got ${BASH_VERSION} ..."

    for cmd in jq perl sed; do
        command -v "${cmd}" &>/dev/null || fatal "command '${cmd}' is missing"
    done

    declare version
    version=$(\jq --version 2>&1 | \awk -F'[ -]' 'OFS="-" {$1="";gsub("^-+","",$0)}1')
    printf '1.6\n%s' "${version}" | \sort -CV || fatal "\jq 1.6+ is required, got ${version} ..."
}

fatal() {
    printf -- "Error: %s\n" "${@}" >&2
    exit 1
}

stderr() {
    printf -- "%s\n" "${@}" >&2
}

get_account_id() {
    \aws sts get-caller-identity --query 'Account' --output text | grep . || {
        stderr "Refresh credentials with command:" ""
        stderr "  \"\${AWSCONNECT_DIR}/awsconnect\" --role ${AWS_PROFILE}" ""
        fatal "Access denied"
    }
}

get_account_name() {
    echo "${AWS_PROFILE}" | \grep  -oP '\K(^W.-....)(?=-role_(DEVOPS|OPERATIONS)$)' || {
        fatal "Could not get account name from AWS_PROFILE=${AWS_PROFILE}"
    }
}

find_secret_arn() {
    local region="${1}"

    stderr "> finding secret ARN in ${region} region ..."

    \aws secretsmanager list-secrets \
        --region "${region}" \
        --filter "Key=tag-key,Values=aws:cloudformation:logical-id" "Key=tag-value,Values=SlackWebHook" \
        --query "SecretList[?ends_with(Tags[?Key=='aws:cloudformation:stack-name']|[0].Value, '-CFN-NOTIFICATION-LAMBDA')][ARN]" \
        --output text \
        || {
            fatal "could not load secrets from ${region} region"
        }
}

read_secret_value() {
    local arn="${1}"
    local region

    stderr "> reading value of ${arn} secret ..."

    region=$(echo "${arn}" | awk -F: '{print $4}')

    \aws secretsmanager get-secret-value \
        --region "${region}" \
        --secret-id "${arn}" \
        --query 'SecretString' \
        --output text \
        || {
            fatal "could not get ${arn} secret value"
        }
}

update_secret_value() {
    local arn="${1}"
    local value="${2}"
    local region

    stderr "> updating value of ${arn} secret ..."

    region=$(echo "${arn}" | awk -F: '{print $4}')

    \aws secretsmanager put-secret-value \
        --region "${region}" \
        --secret-id "${arn}" \
        --secret-string "${value}" \
        --query 'VersionId' \
        --output text \
        || {
            fatal "could not put ${arn} secret value"
        }
}

main() {
    test -z "${DEBUG}" || {
        enable_debug "${DEBUG_FILE}"
        : "Sourced=${IS_SOURCED:-0}"
        : "WorkDir=${WORK_DIR}"
        stderr "# sending debug stream into ${DEBUG_FILE##*/} file in current directory ..."
    }

    ! \grep -Eq "(^|\s)--help|-h(\s|$)" <<< "$*" || usage

    export AWS_PAGER=

    echo "Hub&Spoke - cross-region monitoring SlackWebHook secret sync"
    echo
    echo "> initializing ..."

    unset AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION

    check_requirements
    account_id=$(get_account_id)
    account_name=$(get_account_name)
    main_secret_arn=$(find_secret_arn "${MAIN_REGION}")

    echo
    echo "Ready to sync ${main_secret_arn} value with ${#REST_REGIONS[@]} other regions in ${account_name} (#${account_id}) account!"
    read -r -p "Proceed? <Enter> or ^-C to cancel "
    echo

    main_secret_value=$(read_secret_value "${main_secret_arn}")

    missing_regions=()
    updated_regions=()
    skipped_regions=()

    for region in "${REST_REGIONS[@]}"; do
        echo
        secret_arn=$(find_secret_arn "${region}")

        if test "${secret_arn}" == ""; then
            stderr "WARN: no secret found in ${region} region, skip"
            missing_regions+=("${region}")
            continue
        fi

        secret_value=$(read_secret_value "${secret_arn}")

        if test "${secret_value}" == "${main_secret_value}"; then
            echo "value is up-to-date, skip"
            skipped_regions+=("${region}")
            continue
        fi

        version_id=$(update_secret_value "${secret_arn}" "${main_secret_value}")
        echo "value is updated, version_id: ${version_id}"
        updated_regions+=("${region}")
    done

    echo
    echo "Result stats:"
    printf " - updated (%2d) : %s\n" "${#updated_regions[@]}" "${updated_regions[*]:-n/a}"
    printf " - skipped (%2d) : %s\n" "${#skipped_regions[@]}" "${skipped_regions[*]:-n/a}"
    printf " - missing (%2d) : %s\n" "${#missing_regions[@]}" "${missing_regions[*]:-n/a}"

    if test "${#missing_regions[@]}" -gt 0; then
        echo
        stderr "WARN: still missing secrets in ${#missing_regions[@]} regions:"
        stderr
        fatal 'verify NOTIFICATION-LAMBDA stack is deployed within these regions'
        exit 9
    fi

    echo
    echo "DONE"
}

main "$@"
