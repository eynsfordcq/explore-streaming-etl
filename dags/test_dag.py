# airflow_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def hello_world():
    print("Hello, World!")

with DAG(
    dag_id='hello_world_dag',
    schedule_interval='* * * * *',
    start_date=datetime(2023, 10, 1),
    catchup=False,
) as dag:

    hello_task = PythonOperator(
        task_id='hello_task',
        python_callable=hello_world,
    )

hello_task