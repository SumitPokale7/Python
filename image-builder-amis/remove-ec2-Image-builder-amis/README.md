
# Project Title

A brief description of what this project does and who it's for

### Overview
This script deletes an AMI and its backing snapshot(s) from all AWS Regions in a single AWS Account, if it was created by EC2 Image Builder.

### How to use the script
Script is run from a command line.

Authenticate with AWS and configure the AWS Profile to use.

1. export AWS_PROFILE
```bash
    python3 ami_cleanup_unshared.py
```
### Delete AMI, Snapshots and CFN 

2. export AWS_PROFILE
```bash
    python3 ami_cleanup.py
```

### Delete None Latest and Old AMI's 

3. Source to hub account with {hub_name}-role_OPERATIONS
```bash
    python3 ami_cleanup_none_latest.py
```

# how to use ami_cleanup_none_latest.py:

The script is targetted to delete spoke accounts AMI's with the snapshot associated to them.

There are two options.
1. Delete snapshots older than the cut off date including Latest.
        # Define the cutoff date (June 1, 2024)
        cutoff_date = datetime(2024, 6, 1)
2. Delete all the snapshots other than Latest

# Sample execution
sahan.perera@Sahan-Perera's-MacBook---C02DG27NML7H remove-ec2-Image-builder-amis % python ami_cleanup_none_latest.py
WH-00H1
Delete old AMIs before the cutoff date (e.g., input format 2024-6-1): (Leave blank to skip): 2024-6-1
Delete AMIs with no Latest Tag (Y/N): Y
WH-00H1
WH-00H1
Getting AMI(s) in eu-west-1 tagged as [{'Name': 'tag:CreatedBy', 'Values': ['EC2 Image Builder']}]


# how to use ami_cleanup.py:

    1) This script work basis of Hub (H1/H2/H3), you need to define Hub value in script section and then you required spoke value where the operation being performed 
    
    2) it has a dry-run mode which basically shows how many AMI available with a specific tag and create backup of KMS Keys policies and SSM documents.
    
    3) This script will initially verify if the AMI is running as an instance. If the AMI is associated with an EC2 instance, it will skip the deletion process.

```bash
     python ami_cleanup("dry_run")
     
```

    4) When run without dry-run, it will perform following task:

        a) Delete AMIs
        b) Delete Snapshot
        c) Delete CFN which created for KMS keys replication
        d) Delete SSM documentation
        e) Create backup of KMS policies
        f) Create backup of SSM documents

```bash
     python ami_cleanup()
     
```

    5) How to restore KMS policy: you can use function push_to_server()
    where need to provide region and key name while Hub account value and spoke account will be taken from the Hub declaration section.
    Ex:    
      push_to_server("ap-south-1","mrk-af71795c16fc4c28a4cd551bc8db1ac9")

