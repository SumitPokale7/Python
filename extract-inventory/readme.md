## Overview

This script extracts information from spoke, enterprise, and hub accounts.

The attributes can be amended based on the need

LAMBDAS
runtime, code size, memory size, 
function arn, last modification, 
account id, last execution, cloud watch logs

IAM ROLES
role name, role arn

VPC INFO
cidr block
vpc id

KMS KEY POLICY
instance id, volume id, volume state, key policy alias names

FIREWALL
firewall name, firewall arn


## Requirements and Dependencies

### Assume IAM Role for particular HUB Account

How to run python/bash script locally for the account assuming federated IAM role via AWS Token Broker console
Here is a quick guide:

1. Assume the relevant role via Command Line Interface, for more details please refer to this guide [Onboarding / Offboarding Team Members] (<https://basproducts.atlassian.net/wiki/spaces/CSL/pages/90787714/Onboarding+Offboarding+Team+Members>) in the “AWS Setup“ => “Command Line Interface“ section.

2. Extracting lambda functions within features from spoke accounts
   
   - Set the env parameters: 
   - IS_ENTERPRISE=YES, 
   - HUB_NAMES="WE1-A1,WE1-B1", 
   - EXTRACTION_TYPE=1
   - Set variable EXTRACTION_TYPE=EXTRACT_LAMBDAS
   
3. Extracting roles within features from spoke accounts
   
   - Set the env parameters: 
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE=2
   - ARE_SPOKES_INCLUDED=NO
   - Set variable EXTRACTION_TYPE=EXTRACT_ROLES

4. Extracting vpc information based on a specific tag from spoke accounts
   
   - Set the env parameters:
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE=3, 
   - ARE_SPOKES_INCLUDED=YES
   - KEY_TAG_NAME = "BP-AWS-ADConnectorID"
   - Set variable EXTRACTION_TYPE=EXTRACT_VPCS

5. Extracting cloud formation resources from spoke accounts
   
   - Set the env parameters:
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE=9, 
   - ARE_SPOKES_INCLUDED=YES
   - ACCOUNT_TYPE="Specific"
   - SPECIFIC_ACCOUNT="330428337682"
   - Set variable EXTRACTION_TYPE=EXTRACT_CF
   
6. Extracting provisioned products per service catalog from spoke accounts

   - Set the env parameters:
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE=10, 
   - ARE_SPOKES_INCLUDED=YES
   - Set variable EXTRACTION_TYPE=EXTRACT_PRODUCTS

7. Extracting owned instances from spoke accounts

   - Set the env parameters:
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE: Final = EXTRACT_OWNER_INSTANCES, 
   - ARE_SPOKES_INCLUDED=YES
   - INSTANCE_TAG_CP_NAME = "7771au"
   - ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  
   - ACCOUNT_TYPE = os.getenv("ACCOUNT_TYPE", "ALL") 

8. Extracting CW logs metrics for enterprise accounts

   - Set the env parameters:
   - IS_ENTERPRISE=Yes, 
   - HUB_NAMES="WE1-A1", 
   - EXTRACTION_TYPE: Final = EXTRACT_LG, 
   - ARE_SPOKES_INCLUDED=NO
   - ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  
   - ACCOUNT_TYPE = os.getenv("ACCOUNT_TYPE", "ALL")

9. Extract instance details with domain join or not if the OS is Windows.

   - Set the env parameters:
   - IS_ENTERPRISE=Yes, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE: Final = EXTRACT_DOMAIN_INSTANCES, 
   - ARE_SPOKES_INCLUDED=YES
   - ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  
   - ACCOUNT_TYPE = os.getenv("ACCOUNT_TYPE", "Connected")

10. Tagg the instances if the OS is Windows.
   - Create completed-accounts.csv empty file with account-id as a column in the script directory
   - Set the env parameters:
   - IS_ENTERPRISE=No, 
   - HUB_NAMES="WH-00H1", 
   - EXTRACTION_TYPE: Final = EXTRACT_DOMAIN_INSTANCES, 
   - ARE_SPOKES_INCLUDED=YES
   - ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", "ALL")  
   - ACCOUNT_TYPE = os.getenv("ACCOUNT_TYPE", "Connected")
   - INSTANCE_TAGGING = os.getenv("INSTANCE_TAGGING", True)
   - OS_PLATFORM = os.getenv("OS_PLATFORM", "Windows")
   - TAGGING_DRY_RUN = os.getenv("TAGGING_DRY_RUN", False) : This can be changed to False for tagging


This will extra instance information while when the instance is Windows it will check if the instance is part of domain or not and output the required information.

This follow same extraction method of others
You can use this same as other input parameters.

Running on enterprise account
        
```bash
export REGION=eu-west-1
export ARE_SPOKES_INCLUDED=NO
export IS_ENTERPRISE=YES
export HUB_NAMES=WE1-A1
```

### How to use the script

Script is run from a command line.

1.Setup python environment for the script

```bash
python -m venv .venv
```

2.Activate the environment

```bash
source .venv/bin/activate
```

3.Install requirements

```bash
pip install -r requirements.txt
```


4.Script usage

```bash
cd scripts/extract-inventory/
python extract_inventory.py
```