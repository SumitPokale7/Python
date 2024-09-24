# IaaS: Grant KMS permission for cross-account ASG service linked role

Idempotent script to grant KMS permissions.

## Pre-requisites

- assume access roles:

```shell
$ printf -- '-r %s\n' {AccountName,WU2}-{A1,B1,U1,P1,T1,P2,P3,O2,O3}-role_DEVOPS | xargs -t -- /PATH/TO/awsconnect
```

## Grant permissions

```shell
$ ./kms_grant_asg.sh
```
