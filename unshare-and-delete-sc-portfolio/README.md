## This folder comproses of two scripts as below-

# Script - ushare-and-delete-sc-portfolio.py helps you to ushare and delete a specific aws service catalog portfolio residing in a set of regions.
# Script - delete-cft.py helps you to delete a specific aws cloudformation template residing in a set of regions.

This was implemented under the PBI-5216734 - Link - https://dev.azure.com/bp-digital/AWS%20Platform/_workitems/edit/5216734
You have to provide the API hub account ids eg. H1,H2 and the SC portfolio you want to delete. 

Catalog service configures API Hub Self-Service accounts listed below, to be able to share any Service catalog portfolio to customer spokes via AWS Organizations OUs.

| Branch | Spoke Name | Account ID | HUB env. |
| - | - | - | - |
| develop | WS-Z067 | 886236176633 | H1 |
| staging | WS-Y089 | 899634452187 | H2 |
| master  | WS-00GN | 330428337682 | H3 |

# Follow below instructions while running this script locally.

* Install packages with below command.
  pip3 install -r requirements.txt

* Follow the instructions to create a temp profile credentials given at below link (Point 8)-
 https://basproducts.atlassian.net/wiki/spaces/CSL/pages/4537417947/Onboarding+Tasks+-+New+Joiner

* Provide the input CLI parameters based on env like H1 or H2.
  Then run below script and verify in H1 API hub accounts if portfolio was unshared and deleted.
  
  python3 unshare-and-delete-sc-portfolio.py <PARA 1> <PARA 2> <PARA 3> <PARA 4> <PARA 5> <PARA 6>
  PARA 1 (Required) --> --portfolio-name : string - Portfolio to be deleted<br/>
  PARA 2 (Required) --> --regions : comma separated string of regions - set of resions where the portfolio resides
  PARA 3 (Required) --> --aws-profile : string - AWS local profile to be used to run this session
  PARA 4 (Required) --> --api-account-id : string - AWS env API hub account id
  PARA 5 (Required) --> --role-name: string - Spoke role to be assumed
  PARA 6 (Required) --> --organization-node-type-to-be-unshared : string - Organization node type to be unshared from Portfolio, choices=[ORGANIZATION | ORGANIZATIONAL_UNIT | ACCOUNT]
  e.g.
  1) H1 Env
  python3 unshare-and-delete-sc-portfolio.py  --portfolio-name "PortFolioName" --regions "us-east-1,eu-west-1" --aws-profile "WH-00H1-role_SPOKE-OPERATIONS" --api-account-id "886236176633" --role-name "AWS_PLATFORM_OPERATIONS" --organization-node-type-to-be-unshared  "ORGANIZATIONAL_UNIT"

  2) H2 Env
  python3 unshare-and-delete-sc-portfolio.py --portfolio-name "ServiceCatalogPortfolio-SHARED_PORTFOLIO_AD_CONNECTOR" --regions "ap-southeast-1,ap-southeast-2,us-east-1,eu-west-1,eu-central-1,us-east-2,ap-southeast-3" --aws-profile  "WH-00H2-role_SPOKE-OPERATIONS" --api-account-id "899634452187" --role-name "AWS_PLATFORM_OPERATIONS" --organization-node-type-to-be-unshared "ORGANIZATIONAL_UNIT"

* To delete a cloudformation stack with name using script delete-cft.py
  python3 delete-cft.py <PARA 1> <PARA 2> <PARA 3> <PARA 4> <PARA 5>
  PARA 1 (Required) --> --portfolio-name : string - Portfolio to be deleted<br/>
  PARA 2 (Required) --> --regions : comma separated string of regions - set of resions where the portfolio resides
  PARA 3 (Required) --> --aws-profile : string - AWS local profile to be used to run this session
  PARA 4 (Required) --> --api-account-id : string - AWS env API hub account id
  PARA 5 (Required) --> --role-name : string - Spoke role to be assumed
  
  e.g.
  1) H1 Env
  python3 delete-cft.py  --portfolio-name "Cft-Name" --regions  "us-east-1,eu-west-1" --aws-profile "WH-00H1-role_SPOKE-OPERATIONS" --api-account-id "886236176633" --role-name "AWS_PLATFORM_OPERATIONS"

  2) H2 Env
  python3 delete-cft.py --portfolio-name "Cft-Name" --regions  "ap-southeast-1,ap-southeast-2,us-east-1,eu-west-1,eu-central-1,us-east-2,ap-southeast-3" --aws-profile "WH-00H2-role_SPOKE-OPERATIONS" --api-account-id "899634452187" --role-name "AWS_PLATFORM_OPERATIONS"

