* the execution format is similar to the predecessor, the extraction type is picked-up and rest is same
* the difference is the concurrent execution and passing parameter
* the concurrency is implemented by ThreadpoolExecutor, the program flow is split into preparation and fetching results
  * SUBMIT_LIMIT_PER_PREP = 200 -> based on computer this value can be increased to 200 
  * SUBMIT_LIMIT_PER_FETCH = 200 -> based on computer this value can be tailored between 10 and 200, the higher values return aws throttling errors
* The passing parameter is based on tuple to leverage threadpool executor map
  * every extraction function has same parameter combination
  * single parameter is passed, it is decomposed inside the function
* additionally, there is a resuming option. At some point during the fetching results, the aws kills the hub session and you need to rerun the script.
* to be able to resume go to the line 142 ' _accounts_dict = read_accounts_from_file("accounts.csv", "<account_id>")'
* replace the account_id with the one reported during the exception
* when the second time the program runs it will resume from this account and go further
* since the account id is sorted, it will cover the rest of the accounts accordingly

Notes:
In H3 environments, there are 1,331 accounts as of now 22nd Sep 2023. When the script runs for 16 regions
and all accounts, the aws stops responding when the 50% of accounts are processed. In this case, the script
safely saved the processed accounts to resume accordingly. To resume the procecessing, you should check the
report and see the latest account that was processed. This account id will be the lower bound for the resume 
operation and the script will start from there. 

Here are the instructions:
* after first execution is stopped due to exceptions, you should update the correspondent line as below.
* run the script as is
* in the end there will be two reports and aggregate them to see the whole picture

```commandline
_accounts_dict = read_accounts_from_file("accounts.csv", <NEXT_ACCOUNT_ID_OF_THE_LATESTS_PROCESSED_ONE>)
_accounts_dict = read_accounts_from_file("accounts.csv", "275487448003")

```
