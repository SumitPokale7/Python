#!/bin/bash
# A simple script to set a default profile for the individual Enterprise and Shared IaaS account
# and run the python script against it.

set -e

if [[ "$#" -ne 2 ]]
then
    echo "Deployment script SH file - Missing argument!"
    echo "Usage:"
    echo "$0 <IAAS_ACC_NAMES> <ROLE_SUFFIX>"
    echo "Example:"
    echo "AccountName-A1 WU2-A1 -role_NETWORK-ADM"
    exit 1
fi

IAAS_ACC_NAMES="${1}"
ROLE_SUFFIX="${2}"
OSAKA_REGION="ap-northeast-3"

# Iterates through list and sets AWS default profile for the each Enterprise IaaS account
# And runs python script against it
for acc in $IAAS_ACC_NAMES;
do
    export AWS_PROFILE=${acc}${ROLE_SUFFIX}
    ./delete-default-vpc-iaas.py --iaas_account_name "${acc}" --region "${OSAKA_REGION}"
done
