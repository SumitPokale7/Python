## This folder comprises of one script as below-

# Script - delete-iam-role.py helps you to delete a list of aws iam roles provided in an input file for a specific env

This was implemented under the PBI-5841787 - Link - https://dev.azure.com/bp-digital/AWS%20Platform/_workitems/edit/5841787
You have to provide the hub account ids, a role to be assumed and a input role file. 

Below are the hubs details-

| Hub Name | Account ID | HUB env. |
| - | - | - |
| WH-00H1 | 423499082931 | H1 |
| WH-00H2 | 550590017392 | H2 |
| WH-00H3 | 550772936474 | H3 |

# Follow below instructions while running this script locally.

* Install packages with below command.
  pip3 install -r requirements.txt

* Follow the instructions to create a temp profile credentials given at below link (Point 8)-
 https://basproducts.atlassian.net/wiki/spaces/CSL/pages/4537417947/Onboarding+Tasks+-+New+Joiner

* Provide the input CLI parameters based on env like H1,H2 or H3.
  Based on the input csv file and the roles associated with the specific hub environment, choose a specific profile.
  H1 profile - WH-00H1-role_OPERATIONS
  H2 profile - WH-00H2-role_OPERATIONS
  H3 Profile - WH-00H3-role_OPERATIONS

  Input role csv file format -
  AccountID,AccountName,RoleName
  372584247317,WS-XU07,WS-XU07-TestRoleToDelete

  Then run below script by providing the input parameters.
  
  python3  delete-iam-role.py <PARA 1> <PARA 2> <PARA 3> <PARA 4> <PARA 5> 
  PARA 1 (Required) --> --input-file-path : string - input role csv file path <br/>
  PARA 2 (Required) --> --aws-profile : string - AWS local profile to be used to run this session
  PARA 3 (Required) --> --hub-account-id : string - AWS env hub account id
  PARA 4 (Required) --> --iam-role-to-be-assumed: string - Spoke role to be assumed
  PARA 5 (Optional) --> --dry-run: string - allowed values (True/False), default true

  e.g.
  1) H1 Env
   python3 delete-iam-role.py --aws-profile  "WH-00H1-role_OPERATIONS" --hub-account-id "423499082931"  --input-file-path "IputFilePath.csv"  --iam-role-to-be-assumed "AWS_PLATFORM_ADMIN" --dry-run False

  2) H2 Env
   python3 delete-iam-role.py --aws-profile  "WH-00H2-role_OPERATIONS" --hub-account-id "550590017392"  --input-file-path "IputFilePath.csv"  --iam-role-to-be-assumed "AWS_PLATFORM_ADMIN" --dry-run False
  
  3) H2 Env
   python3 delete-iam-role.py --aws-profile  "WH-00H3-role_OPERATIONS" --hub-account-id "550772936474"  --input-file-path "IputFilePath.csv"  --iam-role-to-be-assumed "AWS_PLATFORM_ADMIN" --dry-run False

* If no --dry-run flag is set or set to 'True', the code logic just iterate through each role and logs in log file that this operation could have deleted the role.
  If --dry-run flag is set or set to 'False', it will actually execute the script and perform the role deletion logic.

* It creates one log file and an output csv file with status.
  Output file format - 
  AccountID,AccountName,RoleName,Status
  245170926532,WS-X00U,WS-X00U-TestRoleToDelete,Role doesn't exist

* The role status in the output file can be -
  Assume role issue (In case the role inside an account is not assumable)
  Role was not deleted as the dry run flag was set to true (In case dry run flag was 'True')
  Role doesn't exist (In case the role doesn't exist)
  Role deleted (Role deletion operation success)
  Role has permission boundary attached (Skipped role deletion due to permission boundary attached)
  Role deletion failed (Due to failure of removal/deletion of attached policies or due to any exception)


