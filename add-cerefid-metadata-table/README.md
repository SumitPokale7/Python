# Purpose

CERefID was introduced to allow for active directory structures to be managed on cloud environment basis (aws account). This has only been populated for new accounts via ServiceNow and we need to retrospectively add for older accounts to support AD Connector across all AWS accounts.

# Usage

Authenticate to AWS using `awsconnect`. Ensuring the typical AWS credentials are set properly in your shell environment. Set your `AWS_DEFAULT_PROFILE` to point to the environment you wish to perform updates to.

```
pip install -r requirements.txt
python3 main.py -f ./data/x00k.csv -t WH-X00K-DYN_METADATA to perform dry run
python3 main.py -f ./data/x00k.csv -t WH-X00K-DYN_METADATA --no-dry-run to perform live changes
```