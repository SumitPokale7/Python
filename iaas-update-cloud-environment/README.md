# Update Cloud Environments on IaaS accounts

This script allows to synchronize mapped `cloud-environment` tags to DynamoDB table per account.

## Pre-requisites

**Note**: following commands should run within `iaas_update_cloud-environment` directory.

Prepare virtual environment:

```shell
export PIPENV_VENV_IN_PROJECT=1
export PIPENV_IGNORE_VIRTUALENVS=1
export PIPENV_NO_INHERIT=1
export PIPENV_YES=1

pipenv --site-packages
```

Install dependencies required to perform the sync:

> **Note**! verify versions of desired packages in `Pipfile` file.

```shell
pipenv install --dev
```

validate if correct version was installed:

```shell
pipenv run pip list | grep -i cloud
```

## Syncing DDB tags

Pass account aliases as arguments to the `sync_tags.py` script:

```shell
pipenv run ./sync_tags.py WE1-A1 WU2-A1
```

There is no need to prepare roles in advance. Once script is launched, it will check current credentials and provide instructions, if these needs to be updated:

```shell
$ pipenv run ./sync_tags.py WE1-A1 WU2-B1
Starting ...
2021-04-23 07:52:57,529 | INFO | [WE1-A1] resolving account ...
2021-04-23 07:52:58,119 | INFO | [WU2-B1] resolving account ...
Error: found 1 not authorized roles: WU2-B1-role_DEVOPS
  Refresh credentials:
    /path/to/awsconnect --role WU2-B1-role_DEVOPS
  And try again!
```
