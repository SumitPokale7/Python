# Enable S3 Storage Lens

AWS Documentation on [Using Amazon S3 Storage Lens with AWS Organizations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens_with_organizations.html) page.

## Usage

Get help as:

```shell
$ ./enable_s3_storage_lens.sh -h
```

Run without confirmation:

```shell
$ FORCE=1 ./enable_s3_storage_lens.sh <cmd> [arg1] ...
```

Run with debug log:

```shell
$ DEBUG=1 ./enable_s3_storage_lens.sh <cmd> [arg1] ...
# sending debug stream into enable_s3_storage_lens.sh.dbg file in current directory ...
```

Then review `enable_s3_storage_lens.sh.dbg` file

### Enable on H&S public hubs

Update following settings in `enable_s3_storage_lens.sh` file, if needed:

- `H1_DELEGATED_IDS` - account ids to be delegated in H1 hub
- `H2_DELEGATED_IDS` - account ids to be delegated in H2 hub
- `H2_DELEGATED_IDS` - account ids to be delegated in H3 hub

Then run sync as follows:

```shell
$ ./enable_s3_storage_lens.sh hs        # all public hubs: H1 H2 H3
$ ./enable_s3_storage_lens.sh hs h1     # only H1 public
$ ./enable_s3_storage_lens.sh hs h2 h3  # only H2 & H3 public hubs
```

Detailed output of H3 sync:

```shell
$ ./enable_s3_storage_lens.sh hs h3

[INFO] Syncing H&S hubs: H3
Proceed with sync? <Ctrl-C> to cancel ...
Activation of S3 Storage Lens using WH-00H3-role_DEVOPS role ...
  checking WH-00H3-role_DEVOPS role access ...
  enabling trusted access ...
  deletaging administration to 2 account(s) ...
  439344466251 - checking account ...
  439344466251 - delegating WS-00GU account ...
  439344466251 - account WS-00GU is delegated successfully
  336431995308 - checking account ...
  336431995308 - account WS-00BP is already delegated
  complete list of delegated administrators:
    - 439344466251	WS-00GU
    - 336431995308	WS-00BP
Activation of S3 Storage Lens using WH-00H3-role_DEVOPS role COMPLETED
```

### Enable os H&S personal dev hub

No hardcoded configuration for personal dev, just envvars:

```shell
export PERSONAL_HUB_ROLE="whatever_my_hub_role"
export PERSONAL_HUB_REGION="eu-west-1"
export PERSONAL_DELEGATED_ID="123456789012"

$ ./enable_s3_storage_lens.sh hs personal
```
