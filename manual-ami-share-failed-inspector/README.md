# Manual Sharing of AMI 

This script allows to manually share the IB Build AMI in an event of inspector finding high vulernability.
For more info visit: https://basproducts.atlassian.net/wiki/spaces/CSL/pages/4165697744/High+Vulnerability+Workaround+-+Manual+Steps

## Pre-requisites

clone tools-script repo

**Note**: following commands should run within `manual-ami-share-failed-inspector` directory.

Install argparse package dependencies:

```shell
pip install -r requirements.txt
```
Create H3 session who has rights to work on IB e.g. DevOps:

```
e.g.
export AWS_DEFAULT_PROFILE=WS-01AW-role_DEVOPS; awsconnect -r WS-01AW-role_DEVOPS

```
Usage in H3 to copy one perticular OS's AMI with other region and share with the org:

```
Usage example: ./share_image.sh ami-084b1299f668207c0 768961172930 WIN16
```
The logs should be written in copy_image.log

