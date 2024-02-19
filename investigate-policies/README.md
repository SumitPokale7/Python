### Overview
This script generates a CSV report with all the resources that are using an IAM Policy in all accounts in the AWS Organization

**Input** - policy names defined in the script in form of a list:
- arn:aws:iam::aws:policy/AdministratorAccess
- arn:aws:iam::aws:policy/PowerUserAccess

**Output** - CSV with the following columns:
- AWS account ID
- AWS account name (as reported by the AWS Organisation or Metadata DDB table
- Resource type (IAM Role, IAM Group, IAM User)
- Resource ARN

### How to use the script
Script is run from a command line.
1. Install requirements
```bash
pip install -r requirements.txt
```
2. Export AWS_DEFAULT_REGION to set the region for the HUB account
3. Assume READONLY role in Hub account from a command line (Personal, H1, H2, H3)
4. Run the script
```bash
python policies.py --output-file H1.csv
```
5. Script does the following:
  - lists all spoke accounts in AWS Organization
  - scans AWS Service Catalog to see if spoke account is in the provisioned product list
  - assumes CIP_INSPECTOR role in each spoke account if the account is in the provisioned product list
  - lists entities for policy
  - prints a report to a console and a file (file name defaults to report.csv)


### Script arguments
#### Optional arguments
```bash
--output-file    # File to save the report in, defaults to report.csv
--role-name      # Role name to assume in each spoke account, defaults to CIP_INSPECTOR
--region         # AWS region to use in Spoke accounts, defaults to 'eu-west-1'
```

### Linting
```bash
flake8 --count
```
