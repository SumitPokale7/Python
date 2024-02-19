### Overview
This script deletes an AMI and its backing snapshot(s) from all AWS Regions in a single AWS Account, if it was created by EC2 Image Builder.

### How to use the script
Script is run from a command line.

Authenticate with AWS and configure the AWS Profile to use.

1. export AWS_PROFILE
```bash
python3 ami_cleanup.py
```

