## Overview

This script extracts information from spoke, enterprise, and hub accounts for service catelog and remove them in each account.

1. Removing provisioned products per service catalog from spoke accounts

   - Set the env parameters:
   - IS_ENTERPRISE=NO, 
   - HUB_NAMES="WH-00H1", 
   - REMOVE_TYPE: Final = REMOVE_PRODUCTS, 
   - ARE_SPOKES_INCLUDED=YES
   - Set variable REMOVE_TYPE: Final = REMOVE_PRODUCTS
        
```bash
export REGION=eu-west-1
export ARE_SPOKES_INCLUDED=NO
export IS_ENTERPRISE=YES
export HUB_NAMES=WE1-A1,WE1-B1
```

Set to DevOps role
enterprise_profile = f"{hub_name}-role_DEVOPS"

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

4. awsconnect -r "{hub_name}-role_DEVOPS"

4.Script usage

```bash
cd scripts/remove-servicecatelog/
python remove_ac.py
```

5. Uncomment following lines 74-76 once you are verified the SC list. This will actually remove the SC's

```
                        # logger.info(sc_client.client.terminate_provisioned_product(
                        #     ProvisionedProductName=product_name
                        # ))
```
