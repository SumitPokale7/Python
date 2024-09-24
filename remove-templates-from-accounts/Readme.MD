## This folder comprises of one script as below-

### Script - remove-cad-from-accounts.py fetches the accounts from the organization and removes the CAD from the accounts.

This was implemented as part of the [PBI-6746422](https://dev.azure.com/bp-digital/AWS%20Platform/_workitems/edit/6746422)
You have to provide the hub account name and the IAM role to be assumed to run this script.

Below are the hubs details-

| Hub Name | Hub Enviornment   | 
|----------|-------------------| 
| WH-00H1  | H1                |
| WH-00H2  | H2                |
| WH-00H3  | H3                |

# Follow below instructions while running this script locally.

* Create Virtual enviornment and activate it with below command
  ```bash
    python3 -m venv venv
    source venv/Scripts/activate

* Install packages with below command.
  ```bash
    pip install -r requirements.txt

* Follow the instructions to create a temp profile credentials given at below link (Point 8)-
 https://basproducts.atlassian.net/wiki/spaces/CSL/pages/4537417947/Onboarding+Tasks+-+New+Joiner

* Use the below command to export AWS_DEFAULT_PROFILE
  ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS (Do it for H1, H2 & H3 as required)
  
* Once you export the AWS_DEFAULT_PROFILE, you can verify the profile with below commands
  ```bash
    echo $AWS_DEFAULT_PROFILE
    aws sts get-caller-identity

* Run the script with the below command
  * If you want to run the script in dry-run mode, use the below command
    * For H1
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H1 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0001 --org-units Platform Security
        ```
    * For H2
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H2 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0002 --org-units Platform Security
        ```
    * For H3
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H3 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0003 --org-units Platform Security
        ```
  * If you want to run the script actually and want to enforce the changes, use the below command
    * For H1
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H1 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0001 --org-units Platform Security --no-dry-run
        ```
    * For H2
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H2 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0002 --org-units Platform Security --no-dry-run
        ```
    * For H3
        ```bash
        python remove_templates_from_accounts.py --hub-account WH-00H3 --role-to-assume AWS_PLATFORM_ADMIN --stack-suffix PPARULE --ddb-prefix WH-0003 --org-units Platform Security --no-dry-run

        ```
