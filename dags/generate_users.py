from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="generate_random_users",
    start_date=datetime(2025, 1, 1),
    schedule_interval="* * * * *",
    catchup=False,
    default_args={
        "retries": 0
    }
):
    run_producer = BashOperator(
        task_id="producer_random_user",
        bash_command="/opt/bitnami/airflow/venv/bin/python /app/producer/producer_random_user.py"
    )

    run_producer