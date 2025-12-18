#!/bin/bash

#Add folders as needed.
folders=(dags plugins)

for host in <node2> <node3>; do
    for folder in ${folders[@]}; do
        rsync -avzh --delete --exclude '__pycache__' --progress /data/airflow/$folder $host:/data/airflow/
    done
done
