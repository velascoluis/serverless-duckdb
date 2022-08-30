# DuckDB Serverless deployment at GCP

This repository contains code to deploy a [Cloud Run serverless endpoint](https://cloud.google.com/run) that is able to execute arbitrary SQL queries wit the following execution workflow:
- Data (tables) should be staged on [GCS](https://cloud.google.com/storage) in [PARQUET](https://parquet.apache.org/) format
- If there is already a  [duckdb catalog file](https://duckdb.org/docs/connect) it should be staged as well at GCS, it will be read upon start and uploaded at the very end to save any potential changes (e.g. table creation)
- As a new query arrives, we parse the referenced tables and create a global python dict loading the corresponding Parquet tables into [Arrow Datasets](https://arrow.apache.org/docs/python/dataset.html), which are then registered at duckDB. If the container is still alive, subsequenta calls can reuse the [global python dict to avoid scanning the tables over and over](https://cloud.google.com/run/docs/tips/general#using_global_variables).
- Data is sent back in JSON format

## Deployment

- Clone repository: 
```bash
$> git clone https://github.com/velascoluis/serverless-duckdb.git
$> cd serverless-duckdb
```
- Launch a cloud Shell with an user with enough permisions (e.g. project owner) and create a new GCS bucket and upload demo customers table:

```bash
$> gsutil mb -c standard -l us-central1 gs://<BUCKET_NAME>
$> gsutil cp -R test_data/customers/ gs://<BUCKET_NAME>/data/customers
```
- Build the Cloud Run service, edit the `build_cloud_run.sh` adapting the variables:
    - `SERVICE_NAME`
    - `REGION`
    - `PROJECT_ID`
```bash
$> ./build_cloud_run.sh
````

- Wait for the service to be deployed and copy the URL, then execute a query against the endpoint, you need to provide 3 parameters:
    - `sql_query`: The SQL to execute 
    - `bucket_name`: The bucket with the data
    - `db_file`: Your duckDB catalog dbfile, a new one will be created the first time you use the database.
    
## Example use

From a terminal run the following command changing CLOUD_RUN_ENDPOINT, BUCKET_NAME and DB_FILE_NAME

```bash
#First call
$> time curl -X GET 'https://<CLOUD_RUN_ENDPOINT>/?sql_query=select%20count(gender),%20gender%20from%20customers%20where%20PhoneService=%27Yes%27%20group%20by%20gender&bucket_name=<BUCKET_NAME>&db_file=<DB_FILE_NAME>'
[{"count(gender)":2163,"gender":"Female"},{"count(gender)":2300,"gender":"Male"}]
real    0m3.613s
user    0m0.017s
sys     0m0.014s
#Extract from container log:
#2022-08-30T09:15:00.296854ZINFO:root:Loading table:customers

#Second call
$> time curl -X GET 'https://<CLOUD_RUN_ENDPOINT>/?sql_query=select%20count(gender),%20gender%20from%20customers%20where%20PhoneService=%27Yes%27%20group%20by%20gender&bucket_name=<BUCKET_NAME>&db_file=<DB_FILE_NAME>'
[{"count(gender)":2300,"gender":"Male"},{"count(gender)":2163,"gender":"Female"}]
real    0m0.967s
user    0m0.015s
sys     0m0.011s
#Extract from container log: 
#2022-08-30T09:15:03.342777ZINFO:root:Table:customers already in memory
```

