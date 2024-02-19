# [H&S] Investigate who uses public AMIs in Federated Account: investigate-public-amis

This code aims to to list all the owners and accounts in regards of the instances based on public AMIs.

The script reports on the following info in CSV format:

* Ami ID
* Ami description
* Owner
* Account number
* Instance ID
* Instance region
* AWS Organizational unit

### Method used

* Assume READONLY role in Hub accounts (H1, H2, H3) to list spoke accounts in Organization
* Then assume CIP_INSPECTOR role in each spoke and list EC2 instances based on public AMIs

### How to use the script
Script is run from a command line.
1. Assume READONLY role in Hub account from a command line (Personal, H1, H2, H3)
2. Run the script
```bash
python public-amis.py --output-file H1.csv
```
3. Script does the following:
  - lists all spoke accounts and OUs spoke accounts belong to in AWS Organization
  - assumes CIP_INSPECTOR role in each spoke account
  - lists instances in all regions supplied as a list in the script
  - gets information about ami images EC2 instances use in each region
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
