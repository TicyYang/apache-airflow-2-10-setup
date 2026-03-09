from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import timedelta


default_args = {
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'execution_timeout': timedelta(seconds=300)
}

with DAG(
    dag_id='sync_dags',
    default_args=default_args,
    schedule_interval=None,
    tags=['maintenance']
) as dag:
    
    scp = BashOperator(
        task_id='scp',
        bash_command='for host in <node2> <node3>; do scp -r ${AIRFLOW_HOME}/dags $host:${AIRFLOW_HOME}/; done',
        queue='node-1'
    )
