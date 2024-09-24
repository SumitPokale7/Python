Manages cases in AWS Support

#### Target spokes are 
- not hub
- account type is Connected
- status is Active or Provision or Provisioning or Quarantine


CASE BREAKDOWN
- categoryCode=service-code-ec2-systems-manager
- caseId=case-114083774797-muen-2024-8fc2ff9c962aca8b
- subject=Limit Increase: EC2 Systems Manager
- status=pending-customer-action

1. Update the local env var based on the table below:
    
    | Environments | DDB_PREFIX | AWS_DEFAULT_PROFILE     |
    |--------------|:-----------|:------------------------|
    | H1           | WH-0001    | WH-00H1-role_OPERATIONS |
    | H2           | WH-0002    | WH-00H2-role_OPERATIONS |
    | H3           | WH-0003    | WH-00H3-role_OPERATIONS |
    
    Example for H1 environment:
    ```bash
    export AWS_DEFAULT_PROFILE=WH-00H1-role_OPERATIONS
    export DDB_PREFIX=WH-0001
    ```

2. how to execute

   in dry run mode results will be written into the cases_YYYY-MM-DD-HH-mm-ss_not_processed.csv
   ```bash
   cd scripts/support-case-manager/
   python3 case_manager.py 
   ```

   in none dry run mode results will be written into the cases_YYYY-MM-DD-HH-mm-ss_processed.csv
   ```bash
   cd scripts/support-case-manager/
   python3 case_manager.py --no-dry-run
   ```

3. pass --account-types-inclusive parameter to target specific account types
   ```bash
   cd scripts/support-case-manager/
   python3 case_manager.py --account-types-inclusive Connected
   ```