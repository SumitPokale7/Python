As of today, below are Transit Gateway route table ID and Transit Gateway ID, to be configured, before executing this script  for migrating to On-prem Transit Gateway Route Table.

```bash
# **H1 Environment - Active, Connected & IaaS Spokes**
# Define environment variables to apply changes to :
# NonProd spokes in Singapore
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='ap-southeast-1'
export TGW_PROD_RT_ID='tgw-rtb-06d752a7f6fbfb1a8'
export TGW_NON_PROD_RT_ID='tgw-rtb-0aff0ec6a5913e75f'
export TGW_ON_PREM_RT_ID='tgw-rtb-03fbb1c6200a78eea'
export TGW_ID='tgw-0fe8f79e54dfcc4fb'

# NonProd spokes in North Virginia
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-1'
export TGW_PROD_RT_ID='tgw-rtb-08cff1cb65ff7e023'
export TGW_NON_PROD_RT_ID='tgw-rtb-0e81e6ff992b8961f'
export TGW_ON_PREM_RT_ID='tgw-rtb-0ebba799fa884ed00'
export TGW_ID='tgw-0ec493341ed049b95'

# NonProd spokes in Ohio 
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-2'
export TGW_PROD_RT_ID='tgw-rtb-00c5d05d4f4aaaac0'
export TGW_NON_PROD_RT_ID='tgw-rtb-0f5d7d1e547bcae38'
export TGW_ON_PREM_RT_ID='tgw-rtb-0940c01775a7b84c8'
export TGW_ID='tgw-0b19c9594611b0fce'

# NonProd spokes in Ireland
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='eu-west-1'
export TGW_PROD_RT_ID='tgw-rtb-0f539fe83e43f7685'
export TGW_NON_PROD_RT_ID='tgw-rtb-0513032c96e6d5d2c'
export TGW_ON_PREM_RT_ID='tgw-rtb-07b2dcd355f4c821f'
export TGW_ID='tgw-09377e6d2abd73921'
# To migrate Prod accounts, configure **ENVIRONMENT_TYPE='Prod'** and run scripts for each region one by one.


# **H2 Environment - Active, Connected & IaaS Spokes**
# Define environment variables to apply changes to :
# NonProd spokes in Singapore
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='ap-southeast-1'
export TGW_PROD_RT_ID='tgw-rtb-06e983e747673c239'
export TGW_NON_PROD_RT_ID='tgw-rtb-042e922dae2dbf9ae'
export TGW_ON_PREM_RT_ID='tgw-rtb-08ec01d449f7684d5'
export TGW_ID='tgw-08760a1561c8b28ca'

# NonProd spokes in North Virginia
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-1'
export TGW_PROD_RT_ID='tgw-rtb-09866fdddaa701d08'
export TGW_NON_PROD_RT_ID='tgw-rtb-0c79e68a215f5707a'
export TGW_ON_PREM_RT_ID='tgw-rtb-098b082db1a3f8cb2'
export TGW_ID='tgw-0150129f5ad08db65'

# NonProd spokes in Ohio 
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-2'
export TGW_PROD_RT_ID='tgw-rtb-086f6f21a6ac4ab51'
export TGW_NON_PROD_RT_ID='tgw-rtb-0f66a2c6d6dceca8d'
export TGW_ON_PREM_RT_ID='tgw-rtb-0b2b258fd91b8e534'
export TGW_ID='tgw-0b63c18a3d3806fd3'

# NonProd spokes in Ireland
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='eu-west-1'
export TGW_PROD_RT_ID='tgw-rtb-002d4cdbc304c8242'
export TGW_NON_PROD_RT_ID='tgw-rtb-0fb11dff554427014'
export TGW_ON_PREM_RT_ID='tgw-rtb-040ee1c64d2c51938'
export TGW_ID='tgw-0c9e2a69cdec3eefe'
# To migrate Prod accounts, configure **ENVIRONMENT_TYPE='Prod'** and run scripts for each region one by one.


# **H3 Environment - Active, Connected & IaaS Spokes**
# Define environment variables to apply changes to :
# NonProd spokes in Singapore
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='ap-southeast-1'
export TGW_PROD_RT_ID='tgw-rtb-02b0e4c909cbcde9d'
export TGW_NON_PROD_RT_ID='tgw-rtb-06278567621a5653e'
export TGW_ON_PREM_RT_ID='tgw-rtb-0f53ee0600ca8cfa9'
export TGW_ID='tgw-09ddc756aec980b44'

# NonProd spokes in North Virginia
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-1'
export TGW_PROD_RT_ID='tgw-rtb-0b3dd61ecfcd2447c'
export TGW_NON_PROD_RT_ID='tgw-rtb-0584e62f15fc66225'
export TGW_ON_PREM_RT_ID='tgw-rtb-0d334559de77f29ec'
export TGW_ID='tgw-0fd67d32ab317c33d'

# NonProd spokes in Ohio 
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='us-east-2'
export TGW_PROD_RT_ID='tgw-rtb-01453384cf21ea3a7'
export TGW_NON_PROD_RT_ID='tgw-rtb-0b2ca5e4e525b7b76'
export TGW_ON_PREM_RT_ID='tgw-rtb-03e78bb4b61ca4e89'
export TGW_ID='tgw-0a4e16d930bba15bd'

# NonProd spokes in Ireland
export ENVIRONMENT_TYPE='NonProd' 
export REGION_FOR_APPLYING_CHANGES='eu-west-1'
export TGW_PROD_RT_ID='tgw-rtb-068ccf742c49a8b40'
export TGW_NON_PROD_RT_ID='tgw-rtb-0f0ccce0a7e2d7a39'
export TGW_ON_PREM_RT_ID='tgw-rtb-04d2f40ca415b8e40'
export TGW_ID='tgw-0787cce2851713313'
# To migrate Prod accounts, configure **ENVIRONMENT_TYPE='Prod'** and run scripts for each region one by one.
