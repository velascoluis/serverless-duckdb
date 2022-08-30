import argparse
import pandas
import json
import os
import logging

from google.cloud import storage
from flask import Flask, request
from sql_metadata import Parser
import pyarrow.dataset as ds
import duckdb


DATA_FORMAT = "parquet"
#Global variable
tables_dict = {}
app = Flask(__name__)

def exec_sql(sql_query,bucket_name,db_file):
    #Get db file name
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    db_file_blob = bucket.blob("metadb/{}".format(db_file))
    if db_file_blob.exists():
        logging.info('duck db definition file found under metadb/{}, it will be reused'.format(db_file))
        db_file_blob.download_to_filename(db_file)
    else:
        logging.info('duck db definition NOT found under metadb/{},a new one will be generated'.format(db_file))
    #Extract tables from sql query and load into arrow datasets
    con = duckdb.connect(database=db_file, read_only=False) 
    table_names = Parser(sql_query).tables
    for table_name in table_names:
        if any(storage_client.list_blobs(bucket_name, prefix="data/{}".format(table_name))):
            if not table_name in tables_dict:
                logging.info('Loading table:{}'.format(table_name))
                tables_dict[table_name] = ds.dataset("gs://{}/data/{}".format(bucket_name,table_name),format=DATA_FORMAT)
            else:
                logging.info('Table:{} already in memory'.format(table_name))
        else:
            return 'table not found : {}'.format(table_name), 400
    #Exec query and return results
    con.register(table_name, tables_dict[table_name])
    con.execute(sql_query)
    df = con.fetchdf()
    logging.info('Uploading back metadb/{}'.format(db_file))
    db_file_blob.upload_from_filename(db_file)
    return df.to_json(orient="records")


@app.get("/")
def main():
    """ Executes a SQL query using duckdb as engine.
   :param str sql_query: The SQL query to exec 
   :param str bucket_name: A GCS bucket containing both the data (under data directory) and the duckdb definition file (under metadb)
   It is expected that each of the tables beign referenced by the SQL query to exists under the data/<table_name> directory on PARQUET format 
   :param str db_file: The name of the duckDB definition file
   :return: SQL query results
   :rtype: dict
   :raises BadRequest
    Example call:
    http://127.0.0.1:8080/?sql_query=select%20*%20from%20customers&bucket_name=velascoluis-dev-sandbox-warehouse&db_file=my_duckdb.db
    """ 
    logging.getLogger().setLevel(logging.INFO)
    logging.info('Executing SQL with duckDB ..')

    if 'sql_query' in request.args:
        sql_query = request.args.get("sql_query",type=str)
        logging.info('sql_query:{}'.format(sql_query))
    else:
        return 'sql_query not provided - bad request!', 400
    if 'bucket_name' in request.args:
        bucket_name = request.args.get("bucket_name",type=str)
        logging.info('bucket_name:{}'.format(bucket_name))
    else:
        return 'bucket_name not provided - bad request!', 400
    if 'db_file' in request.args:
        db_file = request.args.get("db_file",type=str)
        logging.info('db_file:{}'.format(db_file))
    else:
        return 'db_file not provided - bad request!', 400

    return exec_sql(sql_query,bucket_name,db_file)
   
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
