#!/usr/bin/env bash
#
#/ Enable AWS S3 Storage Lens on organization level
#/
#/ Usage: <SELF_NAME> [-h|--help] <command>
#/     hs       - perform H&S sync, idempotent
#/                usage: <SELF_NAME> hs [h1|h2|h3|personal] ...
#/     iaas     - perform IaaS sync, idempotent
#/                usage: <SELF_NAME> iaas [A1] [B1] ...
#/
#/ Environment variables:
#/     DEBUG=1  - troubleshoot logic using <SELF_NAME>.dbg file
#/     FORCE=1  - enforce action
#

set -eu -o pipefail -o errtrace -o functrace
test "${BASH_VERSINFO[0]}" -lt 4 || shopt -s inherit_errexit nullglob compat"${BASH_COMPAT=42}"

# === configuration === #

: "${PERSONAL_HUB_ROLE:=}"
: "${PERSONAL_HUB_REGION:=}"
: "${PERSONAL_DELEGATED_ID:=}"

H1_DELEGATED_IDS=(
    "042967649369"  # WS-Z003: integration tests spoke (develop)
)

H2_DELEGATED_IDS=(
    "891244521389"  # WS-Y003: integration tests spoke (staging)
)

H3_DELEGATED_IDS=(
    "439344466251"  # WS-00GU: integration tests spoke (master)
    "336431995308"  # WS-00BP: #2273859 - https://bp-vsts.visualstudio.com/AWS_CIP/_workitems/edit/2273859
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

main() {
    test -z "${DEBUG}" || {
        enable_debug "${DEBUG_FILE}"
        : "Sourced=${IS_SOURCED:-0}"
        : "WorkDir=${WORK_DIR}"
        stderr "# sending debug stream into ${DEBUG_FILE##*/} file in current directory ..."
    }

    ! \grep -Eq "(^|\s)--help|-h(\s|$)" <<< "$*" || usage

    check_requirements

    declare cmd="${1:-}"
    shift || :

    case "${cmd,,}" in
    hs)     cmd_sync_hs "$@" ;;
    iaas)   cmd_sync_iaas "$@" ;;
    *)      usage "invalid command specified" ;;
    esac
}

cmd_sync_hs() {
    declare accounts=( "${@^^}" )

    # NOTE: PERSONAL must NOT be included into default set
    test "${#accounts[@]}" -gt 0 || accounts=( "H1" "H2" "H3" )

    echo "[INFO] Syncing H&S hubs: ${accounts[@]}"

    confirm_action

    for account in "${accounts[@]}"; do
        case "${account}" in
        PERSONAL)
            test -n "${PERSONAL_HUB_ROLE}" || fatal "envvar PERSONAL_HUB_ROLE has to be configured"
            test -n "${PERSONAL_HUB_REGION}" || fatal "envvar PERSONAL_HUB_REGION has to be configured"
            test -n "${PERSONAL_DELEGATED_ID}" || fatal "envvar PERSONAL_DELEGATED_ID has to be configured"

            activate_s3_storage_lens "${PERSONAL_HUB_ROLE}" "${PERSONAL_HUB_REGION}" "${PERSONAL_DELEGATED_ID}"
            ;;
        H1) activate_s3_storage_lens "WH-00H1-role_DEVOPS" "eu-west-1" "${H1_DELEGATED_IDS[@]}" ;;
        H2) activate_s3_storage_lens "WH-00H2-role_DEVOPS" "eu-west-1" "${H2_DELEGATED_IDS[@]}" ;;
        H3) activate_s3_storage_lens "WH-00H3-role_DEVOPS" "eu-west-1" "${H3_DELEGATED_IDS[@]}" ;;
        *)  fatal "hub ${account} is not configured" ;;
        esac
    done
}

cmd_sync_iaas() {
    fatal "IaaS is not configured or supported"
}

# === functions === #

confirm_action() {
    test -n "${FORCE}" || read -p "Proceed with sync? <Ctrl-C> to cancel ..."
}

run_all_or() {
    declare -r value="$1"; shift
    declare -r values=( "$@" )

    if test "${#values[@]}" -eq 0; then
        return 0  # run for all
    fi

    if [[ ${values[*]} =~ (^|[[:space:]])"${value}"($|[[:space:]]) ]]; then
        return 0  # run for value
    fi

    return 1  # no run
}

guard_envvars() {
    test -n "${AWS_PROFILE}" || fatal "envvar AWS_PROFILE is missing or empty"
    test -n "${AWS_DEFAULT_REGION}" || fatal "envvar AWS_DEFAULT_REGION is missing or empty"
}

guard_session() {
    guard_envvars

    echo "checking ${AWS_PROFILE} role access ..."

    \aws sts get-caller-identity >/dev/null || {
        stderr "Refresh credentials with command:" ""
        stderr "  \"\${AWSCONNECT_DIR}/awsconnect\" --role ${AWS_PROFILE}" ""
        fatal "Access denied"
    }
}

enable_trusted_access() {
    guard_envvars

    echo "enabling trusted access ..."

    \aws organizations enable-aws-service-access \
        --service-principal storage-lens.s3.amazonaws.com
}

delegate_administration() {
    declare -r account_ids=( "$@" )
    declare response

    guard_envvars

    if test "${#account_ids[@]}" -eq 0; then
        stderr "[WARN] no delegated accounts defined for ${role} role"
        return
    fi

    echo "deletaging administration to ${#account_ids[@]} account(s) ..."

    response=$(\aws organizations list-delegated-administrators \
        --service-principal storage-lens.s3.amazonaws.com \
        --query='DelegatedAdministrators[*].[Id]' \
        --output=text)

    declare delegated_ids=()
    readarray -t delegated_ids < <(echo -n "${response}")

    for account_id in "${account_ids[@]}"; do
        echo "${account_id} - checking account ..."

        declare name
        name=$(\aws organizations describe-account --account-id "${account_id}" --query 'Account.Name' --output text)

        if printf '%s\n' "${delegated_ids[@]}" | grep -qxF "${account_id}"; then
            echo "${account_id} - account ${name} is already delegated"
        else
            echo "${account_id} - delegating ${name} account ..."

            \aws organizations register-delegated-administrator \
                --service-principal storage-lens.s3.amazonaws.com \
                --account-id "${account_id}"

            echo "${account_id} - account ${name} is delegated successfully"
        fi
    done

    echo "complete list of delegated administrators:"

    \aws organizations list-delegated-administrators \
        --service-principal storage-lens.s3.amazonaws.com \
        --query='DelegatedAdministrators[*].[Id, Name]' \
        --output=text \
        | sed -e 's/^/- /' \
        | indent
}

activate_s3_storage_lens() {
    declare -r role="${1}"
    declare -r region="${2}"
    shift 2
    declare -r account_ids=( "$@" )

    echo "Activation of S3 Storage Lens using ${role} role ..."

    if test "${#account_ids[@]}" -eq 0; then
        stderr "[WARN] no delegated accounts defined for ${role} role"
        return
    fi

    export AWS_PROFILE="${role}"
    export AWS_DEFAULT_REGION="${region}"

    {
        guard_session
        enable_trusted_access
        delegate_administration "${account_ids[@]}"
    } | indent

    echo "Activation of S3 Storage Lens using ${role} role COMPLETED"
}

# === helpers === #

enable_debug() {
    declare file="$1"

    exec 19> "${file}"
    export BASH_XTRACEFD=19

    shopt -s extdebug

    declare -g DEBUG_START_MS
    DEBUG_START_MS=$(unix_milliseconds)
    readonly DEBUG_START_MS

    export PS4='+ [$(( $(unix_milliseconds) - $DEBUG_START_MS ))ms] at ${BASH_SOURCE[0]}:${LINENO} in ${FUNCNAME[0]:-main}${FUNCNAME[0]:+()} [pid:${BASHPID},sub:${BASH_SUBSHELL},uid:${EUID}] '
    set -x

    : "OS=${OSTYPE}"
    : "Bash=${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}.${BASH_VERSINFO[2]}"
    : "BashOpts=${BASHOPTS}"
}

unix_milliseconds() {
    test "${BASH_VERSINFO[0]}" -lt 5 || {
        date +%s%3N
        return
    }

    echo $(( "${EPOCHREALTIME/./}" / 1000 ))
}

usage() {
    declare err_msg="${1:-}"

    \grep '^#/' "${SELF_FILE}" | \cut -c4- | \sed -e "s/<SELF_NAME>/${SELF_FILE##*/}/"

    test -n "${err_msg}" || exit 0

    echo
    fatal "${err_msg}"
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

indent() {
    \sed -e 's/^/  /'
}

# === main === #

test -n "${IS_SOURCED}" || {
    main "$@"
    exit 0
}
