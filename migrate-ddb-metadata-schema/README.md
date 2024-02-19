# Migrate DDB metadata table schema

This script allow to migrate field schema from old type/value to a new type/value using idempotent approach.

## Usage

```shell
$ export AWS_REGION=eu-west-1
$ export AWS_PROFILE=<HUB_ROLE_PREFIX>-role_DEVOPS
$ export ACCOUNT_PREFIX=<HUB_NAME_PREFIX>

$ ./migrate_ddb_metadata_schema.py

Starting ...

Schema migration on DDB 'WH-XXXX-DYN_METADATA' table in WH-XXXX (111222333444) account.

 - internet-facing: str('Yes') => bool(True)
 - internet-facing: str('No') => bool(False)

Proceed? <Ctrl-C> to abort ...

Migrating 'internet-facing' field from str('Yes') to bool(True) ...
found 2 item(s):
 - WS-XXX1
 - WS-XXX2

Migrating 'internet-facing' field from str('No') to bool(False) ...
found 1 item(s):
 - WS-ZZZ1

DONE
```

**DRY-RUN**: in order to observer execution without real update, pass `-n/--dry-run` argument:

```shell
./migrate_ddb_metadata_schema.py --dry-run
```

To show help and other details, pass common `-h/--help` argument:

```shell
./migrate_ddb_metadata_schema.py --help
```
