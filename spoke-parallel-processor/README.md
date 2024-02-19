# Setup

* Install Docker Desktop
* Authenticate using `aws-connect`
* `cd spoke-parallel-processor`
* fetch your personal access token from azure devops (https://dev.azure.com.mcas.ms/bp-digital/_usersSettings/tokens)
* export `PERSONAL_ACCESS_TOKEN=<PERSONAL_ACCESS_TOKEN_EXPORTED_FROM_AZURE_DEVOPS>``
* export `AWS_DEFAULT_PROFILE` to the role you want to use
* export `ASSUME_ROLE_NAME=<SPOKE_ROLE_TO_ASSUME>`
* export `HUB_NAME=<HUB_NAME>` e.g. `WH-0001`
* export `AWS_DEFAULT_REGION=<REGION_NAME>` e.g. `eu-west-1`
* `docker-compose up`
* Browser > `http://localhost:8888` and watch CLI output from `docker-compose` it will contain a URL along with token. Token is required for access to notebook

## Performance

* Docker Desktop > Settings > Resources - Here you can allocate more CPUs to the docker runtime, therefore giving `Dask` more cores/threads to work with when performing parallelisation.

## Additional Library Requirements

* Add any additional libraries space separated in `docker-compose.yml` and within the `EXTRA_PIP_PACKAGES` env var

## Addition of new notebooks

* Create a new notebook - volume is mounted in docker to your local filesystem so you can modify freely and will be saved to your local (as long as you hit save in Juypter)