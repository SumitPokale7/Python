#!/bin/bash

# A simple script to set a default profile for the individual IaaS account
# and run the python script against it.

set +ex

#############################################################################################################
# PREREQUISITES => You must first assume IAM roles for each IaaS (A1, B1, U1, T1, P1, P2, P3) accounts via AWS Token Broker.
#
#  Step 1. Assume the relevant role via Command Line Interface, for more details please refer to this guide  
# (https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members) 
# in the “AWS Setup“ => “Command Line Interface“ section.
#
#  Step 2. Run the 'awsconnect' file in order to assume the IAM role for each IaaS (A1, B1, U1, T1, P1, P2, P3) account
# for both eu-west-1 & us-east2 regions
# e.g. <path-to-awsconnect-file>/awsconnect --role <account_name-role_DEVOPS --role <account_name-role_DEVOPS> \
#    --role <account_name-role_DEVOPS> --role <account_name-role_DEVOPS> \
#    --role <account_name-role_DEVOPS>  and so on up to WU2-P3 .....
###############################################################################################################


# Iterates through array and sets AWS default profile for the each IaaS account
# And also runs python script for the each IaaS account
declare -a iaas_accounts=(
    "WE1-A1" "WU2-A1"
    "WE1-B1" "WU2-B1"
    "WE1-T1" "WU2-T1"
    "WE1-U1" "WU2-U1"
    "WE1-P1" "WU2-P1"
    "WE1-P2" "WU2-P2"
    "WE1-P3" "WU2-P3"
)

IRELAND="eu-west-1"
OHIO="us-east-2"
OUTPUT_FILE="subnets-report.csv"

for acc in ${iaas_accounts[@]};
do
    if [[ $acc = WE1* ]]; then
    export AWS_DEFAULT_PROFILE=${acc}-role_DEVOPS
    python assess-subnets.py --account-name ${acc} --region  ${IRELAND} --output-file ${OUTPUT_FILE}
    elif [[ $acc = WU2* ]]; then
    export AWS_DEFAULT_PROFILE=${acc}-role_DEVOPS
    python assess-subnets.py --account-name  ${acc} --region  ${OHIO} --output-file ${OUTPUT_FILE}
    fi
done