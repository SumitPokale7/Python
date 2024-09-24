## This folder comprises of one script as below-

# Script - fetch_iam_users.py fetches all the users from the AWS account and writes the output to a csv file.

This was implemented as part of the [PBI-6354344](https://dev.azure.com/bp-digital/AWS%20Platform/_workitems/edit/6354344)
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

* Run the script with below command
    ```bash
      1) H1 Envionment
       python fetch_iam_users.py --hub-account "WH-0001" --role-to-assume "CIP_INSPECTOR"
  
      2) H2 Envionment
       python fetch_iam_users.py --hub-account "WH-0002" --role-to-assume "CIP_INSPECTOR"
    
      3) H3 Envionment
       python fetch_iam_users.py --hub-account "WH-0003" --role-to-assume "CIP_INSPECTOR"