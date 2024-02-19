# Investigate RDS instances which are linked to active accounts
### Overview
This script allow us to investigate which type of accounts are they used for and investigate on actions to move/migrate these instances into DBaaS procured policy of usage.

### CSV Output
- Spoke ID
- Spoke Name
- Region
- Number Of Instances
- DB Instance Identifier
- DB Instance Class
- Allocated Storage
- Engine Size

### How to use the script
Script is run from a command line.
1. Install requirements
```bash
$ pip install -r requirements.txt
```
2. Export AWS_DEFAULT_REGION to set the region for the HUB account
``` bash
$ export AWS_REGION=eu-west-1
```

3. Assume READONLY role in Hub account from a command line (Personal, H1, H2, H3) using bp AWS connect
```bash
$ export AWS_DEFAULT_PROFILE=<HUB_ROLE_PREFIX>-role_READONLY;
$ <PATH_TO>/awsconnect -r "${AWS_DEFAULT_PROFILE}"
```

4. Run the script
```bash
$ ./rds-instances.py --output-file <NAME OF OUTPUT FILE>.csv
```
5. Script does the following:
  - lists all active spoke accounts linked to RDS instance in AWS Organization
  - lists RDS data
  - prints a report to a console and a file (file name defaults to report.csv)

### Script arguments
#### Optional arguments
```bash
--output-file    # File to save the report in, defaults to report.csv
--role-name      # Role name to assume in each spoke account, defaults to CIP_INSPECTOR
```

### Linting
```bash
flake8 --count
```

###Additional Comments
If there are SSL validation issues with us-east-1 (N. Virginia) region then run this script in AWS Cloudshell CLI
