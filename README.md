# Scripts
This repository contains any scripts which were developed to perform ad-hoc tasks.

# Overview

| Script | Purpose |
| ------ | ------ |
| [add-tgw-to-account-metadata](add-tgw-to-account-metadata) | Updates specified accounts metadata with the correct tgw attachments data. |
| [assess-subnets-utilisation](assess-subnets-utilisation) | This script has been developed in order to assess all VPC subnet(s) in particular region for any IaaS account. The script loops through a list of subnets in particular IaaS account and region capturing required subnets' details. Script also generates a CSV report file with required results. |
| [controltower-config-customization](controltower-config-customization) | Override Config Recorder settings to exclude specific resources from Recorder in selected accounts in a Control Tower environment. |
| [copy-tgw-routes](copy-tgw-routes) | Copies TGW Routes from one TGW RT to another. |
| [create-new-ou](create-new-ou) | These are one-off scripts that aim to create OUs in Hub accounts. |
| [create-new-ous](create-new-ous) | Deploy baseline and any additional OUs within an Organization. |
| [dns-stack-redeploy](dns-stack-redeploy) | This is a one-off script that aims to remove remove and recreate a DNS stack for the Connected and Enterprise active accounts. |
| [enable-inspector2](enable-inspector2) | Enable Inspector2. |
| [enable-s3-storage-lens](enable-s3-storage-lens) | Enable S3 Storage Lens. |
| [extract-inventory](extract-inventory) | Iterate over all non-terminated spoke accounts and extract particular information such as lambda functions, roles, vpcs, Log groups, etc. |
| [firewall-subnets](firewall-subnets) | Create a list of AWS Federated accounts using AWS Load Balancers in Firewall Subnets. |
| [hs-monitoring-sync-slack-secret](hs-monitoring-sync-slack-secret) | Cross-region monitoring SlackWebHook secret sync. |
| [iaas-kms-grant-asg](iaas-kms-grant-asg) | Idempotent script to grant KMS permissions. |
| [iaas-cross-accounts](iaas-cross-accounts) | Set of cross account scripts used to traverse IaaS accounts. |
| [iaas-update-cloud-environment](iaas-update-cloud-environment) | Allows to synchronize mapped `cloud-environment` tags to DynamoDB table per account. |
| [investigate-autotagger-tags](investigate-autotagger-tags) | This script generates two CSV report files about resources that are tagged with "cloud-environment" tag and not covered by Autotagger v2.1. One file is a summary of ARNs with a count for each resource/arn type, the oher one is full report of discovered resources. |
| [investigate-platform-cloudtrail](investigate-platform-cloudtrail) | Verifies if any H&S platform deployed cloudtrail is present. |
| [investigate-policies](investigate-policies) | This script has been developed to review the usage of AdministratorAccess and PowerUserAccess or equivalent policy. The script goes through a list of all accounts in AWS Organization and checks what entities (IAM User, IAM Role, IAM Group) AdministratorAccess and PowerUserAccess are attached to. Script writes a csv file as well as prints data to the console. |
| [investigate-public-amis](investigate-public-amis) | This script has been deveoped to investigate usage of publicly available amis on BP platform. The script goes through a list of all accounts in AWS Organization and checks all instances for the image they are using. Script writes a csv file as well as prints data to the console. |
| [investigate-rds-instances](investigate-rds-instances) | Investigate which type of accounts are they used for and investigate on actions to move/migrate these instances into DBaaS procured policy of usage. |
| [investigate-sgs-nacls](investigate-sgs-nacls) | Check inbound security group rules and inbound nacls for public nacl for Standalone-4-Tier-3-AZ spoke accounts. |
| [match-service-to-metadata-version](match-service-to-metadata-version) | Match HS service version to accounts metadata version. |
| [migrate-ddb-metadata-schema](migrate-ddb-metadata-schema) | Migrate field schema from old type/value to a new type/value using idempotent approach. |
| [migrate-spokes-to-control-tower](migrate-spokes-to-control-tower) | Migration script to process accounts for Control Tower migration. |
| [migrate-spokes-tgw-rt](migrate-spokes-tgw-rt) | Move TGW attachment associations from onprem TGW RT to temp TGW RT. |
| [phz-vpc-update](phz-vpc-update) | Associate already existing PHZs to a DNS HUB VPC deployed in a new region. |
| [remove-cloudtrail-resources](remove-cloudtrail-resources) | Remove S3 bucket and CW log group created by the Cloudtrail stack deployed into a spoke by landingzone. This is to clean up after removing the stack from the landingzone configuration. |
| [remove-default-vpc](remove-default-vpc) | This script has been developed in order to delete default VPC from all spokes that has status:"Active" in Osaka (ap-northeast-3) region only. It gets list of all active spokes from Dynamo DB table and iterates through each item connecting via role session. |
| [remove-default-vpc-iaas-enterprise](remove-default-vpc-iaas-enterprise) | This script has been developed in order to delete default VPC from Enterprise and Shared IaaS accounts in Osaka (ap-northeast-3) region only. |
| [remove-ec2-Image-builder-amis](image-builder-amis/remove-ec2-Image-builder-amis) | Deletes an AMI and its backing snapshot(s) from all AWS Regions in a single AWS Account, if it was created by EC2 Image Builder. |
| [remove-flowlog-resources](remove-flowlog-resources) | Removes S3 buckets and CW log groups created by the VPCFlowLog stack deployed into a spoke by landingzone. This is to clean up after removing the stack from the landingzone configuration. |
| [service-quota](service-quota) | Automation to increase the number of routes per route table, VPC service limit on all existing Connected accounts. |
| [stringtobool](stringtobool) | Update the attribute "internet-facing" type from string to bool. Also, it helps changing the values "No","0","off" to False. |
| [tgw-flow-logs](tgw-flow-logs) | Enabe TGW Flow Logs for Transit Gateways across multiple regions. |
| [unshare-image-builder-amis](image-builder-amis/unshare-image-builder-amis) | Unshares AMIs created by Image builder and updates the release-os in specified regions of the account |
| [ushare-and-delete-sc-portfolio](ushare-and-delete-sc-portfolio) | Ushare and delete a specific aws service catalog portfolios, delete a cloudformation stacks residing in a set of regions |
| [investigate-role-boundaries](investigate-role-boundaries) | Audit role usage & policy boundaries
| [iam-role-deletions](iam-role-deletion) | Iam role deletion
| [update-log-group-retention-period](update-log-group-retention-period) | Updates log groups retention period |
