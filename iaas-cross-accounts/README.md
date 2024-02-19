# IaaS cross accounts

This is a set of cross account scripts used to traverse on IaaS account

Each script checks account access credentials and warns if one is missing or expired.

Prepare envvar to refer `awsconnect` directory:

```shell
$ export AWSCONNECT_DIR="${HOME}/workspace/BP/awsconnect"
```

To get more detailed information, run each script with `--help` (`-h`) option, eg:

```shell
$ ./discover_lambdas_py27.py -h
```

## Discover Python2.7 Lambda Functions

discover and generate report within all (18) accounts.

```shell
$ ./discover_lambdas_py27.py {WE1,WU2}-{A1,B1,U1,P1,T1,P2,O2,P3,O3}
```

**Note**: curly braces expansion works in Bash, might not work in other shells

## Generate sanitized lambda names report

We can generate a report with with sanitized lambda names using following command:

```shell
$ cat discover_lambdas_py27.report.json | jq -c 'group_by(.SanitizedName)[]|{SanitizedName: .[0].SanitizedName, accounts: map(.AccountAlias)}' | grep -E -- '-(P1|P2|P3|02|03|T1)' | jq -r '"\(.SanitizedName) - [\(.accounts|join(","))]"'
```

Find functions executed within last 3 months:
```shell
$ cat discover_lambdas_py27.report.json | jq -c '[.[]|select(.ExecutedWithin3Months==true)]|group_by(.SanitizedName)[]|{SanitizedName: .[0].SanitizedName, accounts: map(.AccountAlias)}' | grep -E -- '-(P1|P2|P3|02|03|T1)' | jq -r '"\(.SanitizedName) - [\(.accounts|join(","))]"'
```