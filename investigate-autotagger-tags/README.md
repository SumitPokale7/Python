### Overview
This script generates two CSV report files about resources that are tagged with "cloud-environment" tag and not covered by Autotagger v2.1.
One file is a summary of ARNs with a count for each resource/arn type, the oher one is full report of discovered resources.

**Input** - resource types covered by autotager 2.1
- network-interface
- instance
- loadbalancer
- targetgroup
- security-group
- volume
- snapshot
- image

**Output** - CSV with the following columns:
- ARNs of resources with cloud-environment tag

### How to use the script
Script is run from a command line.
1. Install requirements
```bash
pip install -r requirements.txt
```
3. Assume DEVOPS role (or READONLY role if availabe) in the enterprise account you want to run report for
4. Run the script
```bash
python investigate-resources.py
```
5. Script does the following:
  - gets a list of resources tagged with "cloud-environment" tag
  - prints two CSV report files (example for the WE1-A1 accopunt):
    - WE1-A1-summary.csv
    - WE1-A1-report.csv

### Linting
```bash
flake8 --count
```
