# Update EKS Auth

## Overview

This Python script automates the update of authentication methods for Amazon EKS clusters across an organization. It ensures that each cluster uses both ConfigMap and API methods if they are currently set only to ConfigMap.

## Features

- **Asynchronous Execution:** The script operates asynchronously in batches, handling 20 accounts at a time across all enabled AWS regions.
- **Configuration Flexibility:** Users can customize the execution by modifying the `DISABLED_REGIONS` and `ROLE_NAME` constants to fit specific requirements.
- **Resilience to Interruptions:** If the script is interrupted, it can resume by reading the current list of accounts and skipping those that have already been scanned.

## Requirements

- Python 3.x
- `aioboto3` library

## Configuration

1. **Set Disabled Regions:** Modify the `DISABLED_REGIONS` list in the script to exclude specific regions from the scan.
2. **Set Role Name:** Adjust the `ROLE_NAME` constant to specify the AWS role used for accessing the EKS clusters.

## Usage

Run the script from a command line interface by navigating to the directory containing the script and executing:

```bash
python update_eks_auth.py
```

Ensure that your AWS credentials are configured to have sufficient permissions to modify EKS cluster configurations.

# Contribution

Contributions to the script are welcome.