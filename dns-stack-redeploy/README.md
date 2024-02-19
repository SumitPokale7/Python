# [H&S] 1811311 Deploy DNS Hub spoke VPC and resources for Ohio:
dns-stack-redeploy

This is a one-off script that aims to remove and recreate a DNS stack for the Connected and Enterprise active accounts.
### Method used

* Assume DEVOPS role in Hub accounts (H1, H2, H3) to list all active spoke accounts with dns_version field present in a given region (Ohio). Run the script for those spoke accounts (this can be done in smaller chunks for H3).

### How to use the script
Script is run from a command line.
1. Assume DEVOPS role in Hub account from a command line (Personal, H1, H2, H3)
2. Set the `spoke_list` variable to the accounts you want to perform this action on
3. Run the script (replace the required variables with respective values for the hub)
```bash
sh dns-stack-redeploy.sh <PROFILE_NAME> <HUB_NAME> <HUB_ACCOUNT_NUMBER>
```
 - PROFILE_NAME - aws profile used for the script i.e. WH-00H1-role_DEVOPS
 - HUB_NAME - hub name i.e. 0001
 - HUB_ACCOUNT_NUMBER - account number for the hub i.e. 423499082931

4. Script does the following:
  - script loops through the spokes that are part of a `spoke_list`
  - for each account it invokes a DNS-SERVICE lambda function and deletes the DNS stack
  - after successful DNS stack deletion the DNS-SERVICE lambda is invoked again and the DNS stack is recreated
