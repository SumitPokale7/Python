#Create Package
set -euo pipefail

SELF_FILE=$(\grep -E '^(\.|\/)' <<< "${BASH_SOURCE[0]}" || echo "./${BASH_SOURCE[0]}")
SELF_DIR="${SELF_FILE%/*}"
readonly SELF_FILE SELF_DIR

set -x

pushd "${SELF_DIR}" >/dev/null

echo >> 'Deleting the Cloudformation stack'
aws cloudformation delete-stack \
    --stack-name WH-${ENVIRONMENT}-CFN-TRANSIT-GATEWAY-FLOWLOGS