#!/bin/bash

#Add folders as needed.
folders=(dags plugins)

for host in <node2> <node3>; do
    for folder in ${folders[@]}; do
        rsync -avzh --delete --exclude '__pycache__' --progress ${AIRFLOW_HOME}/$folder $host:${AIRFLOW_HOME}/
    done
done
