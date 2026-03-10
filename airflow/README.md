# Airflow 2.10.5 High-Availability Cluster Setup

This guide demonstrates the deployment of a production-ready Apache Airflow cluster using Celery Executor.

---

## Architecture

| Component \ Server IP  | Node 1 | Node 2 | Node 3 | Node 4 |
| --- |:---:|:---:|:---:|:---:|
| Scheduler        |  O  |  O  |  -  |  -  |
| Webserver        |  O  |  O  |  -  |  -  |
| Worker           |  O  |  O  |  O  |  -  |
| Flower           |  O  |  -  |  -  |  -  |
| MySQL            |  -  |  -  |  -  |  O  |

## Environment

- OS: Ubuntu Server 22.04 LTS
- Docker Compose: `v2.26.1`
- Python: 3.10.12
- Airflow: 2.10.5
- MySQL image tag: `oraclelinux8`


## Install MySQL (Node 4)

1. Create the directory: `mkdir -p docker-mysql/airflow_mysql && cd docker-mysql
`
2. The `mysql/docker-compose.yaml` in this repository can be used directly.
3. Start the container: `docker compose up -d`
4. Enter the container: `docker exec -it mysql-airflow bash`
5. Log in to MySQL: `mysql -u root -p`
6. Database Initialization:
    ```sql
    /* Execute inside MySQL container */
    CREATE DATABASE airflow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'airflow_user'@'%' IDENTIFIED BY 'your_password';
    GRANT ALL PRIVILEGES ON airflow_db.* TO 'airflow_user'@'%';
    ```


## Install Airflow (Node 1)
1. Create directories: `mkdir -p airflow/{dags,logs,plugins}`
2. Configure environment variables: `vi ~/.bashrc`
    ```shell
    # Airflow
    export AIRFLOW_HOME=/data/airflow
    export PYTHONPATH=/data/airflow/script_dir/
    ```
    `source ~/.bashrc`
3. Install Apache Airflow: `pip install apache-airflow==2.10.5`
4. Initialize the database configuration files: `airflow db migrate`
5. Install MySQL client libraries: `sudo apt-get install libmysqlclient-dev -y`
6. Set MySQL client related environment variables: `vi ~/.bashrc`
    ```shell
    export MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
    export MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient -lzstd -lssl -lcrypto -lresolv -lm"
    ```
    `source ~/.bashrc`
7. Install Airflow MySQL provider: `pip install apache-airflow[mysql]`
8. Update the database connection in the configuration file: `vi airflow.cfg`
    Configuration examples can be found in the `airflow.cfg`.

9. Reset the Airflow metadata database: `airflow db migrate`
10. Create an admin user:
    ```shell
    airflow users create \
    --username admin \
    --firstname <firstname> \
    --lastname <lastname> \
    --role Admin \
    --email <email>
    ```


## Install Cluster Related Packages
1. Install Celery and Redis dependencies: `pip install "apache-airflow[celery, redis]"`
2. Edit the configuration file: `vi airflow.cfg`
   Configuration examples can be found in the `airflow.cfg`.


## Startup and Shutdown

- Startup (in Order)
    ```shell
    airflow webserver -p 8080 -D
    airflow scheduler -D
    airflow celery worker -D
    airflow celery flower -D
    ```

- Shutdown (in Order)
    ```shell
    ps aux | grep -v "grep" | grep "airflow" | awk '{print $2}' | xargs kill -9
    
    airflow celery stop

    rm ${AIRFLOW_HOME}/airflow-{webserver,scheduler,webserver-monitor,flower,worker}.pid
    ```


## Set Node 2 & Node 3
### Installation (Same as Node 1)
1. Initialize the database: `airflow db migrate`
   Configuration files will be generated after initialization.
2. Edit the configuration file: `vi airflow.cfg`
    - All settings must be exactly the same as Node 1, except for `default_queue`.
      - Node 2: `default_queue = default,node-2`
      - Node 3: `default_queue = default,node-3`
    - When running more than one webserver, the `secret_key` must be identical across all nodes. Otherwise, logs from individual workers cannot be retrieved.
    - The `flower_basic_auth` setting must be configured even on nodes where Flower is not running.

### Startup
```shell
# Node 2
airflow webserver -D
airflow scheduler -D
airflow celery worker -D

# Node 3
airflow celery worker -D
```


## Run as a System Service
1. Set environment variable: `vi /etc/sysconfig/airflow`
   Add the following line: `AIRFLOW_HOME=/data/airflow`
2. Edit the following files in `/etc/systemd/system/`. Examples can be found in the directory `systemd`.
    - `airflow-webserver.service`
    - `airflow-scheduler.service`
    - `airflow-worker.service`
    - `airflow-flower.service`
3. Reload system services: `systemctl daemon-reload`
4. Using the webserver as an example:
    ```shell
    systemctl enable airflow-webserver
    systemctl start airflow-webserver
    systemctl stop airflow-webserver
    systemctl restart airflow-webserver
    systemctl disable airflow-webserver
    systemctl status airflow-webserver
    ```


## Synchronize DAG files
### Option 1: rsync
1. Create a management directory: `mkdir ${AIRFLOW_HOME}/manage`
2. Create a shell script: `vi ${AIRFLOW_HOME}/manage/sync.sh`
    Shell script examples can be found in the directory `manage`.

### Option 2: Manually trigger synchronization using a DAG
- Create DAG file: `vi ${AIRFLOW_HOME}/dags/sync_dags.py`
- DAG file examples can be found in the directory `dags`.


## Log Management

### Log File Reference
| Component | Filename | Description | Growth (Daily) | Rotation Required |
| --- | --- | --- | :---: | :---: |
| Flower | `airflow-flower.err` | Error messages from Flower; empty if no error. | X | X |
| Flower | `airflow-flower.out` | Flower Web UI URL, connected Broker, and startup information. | X | X |
| Scheduler | `airflow-scheduler.err` | Gunicorn startup, workers, listening ports, and PIDs. | X | X |
| Scheduler | `airflow-scheduler.log` | Duplicate of `.out` content. Empty if started via systemd. | X | X |
| Scheduler | `airflow-scheduler.out` | Active executors and task dispatching records. | O | O |
| Webserver | `airflow-webserver.err` | Webserver Gunicorn startup, workers, ports, and PIDs. | X | X |
| Webserver | `airflow-webserver.log` | Webserver access logs, including Client IP and HTTP Methods. | O | O |
| Webserver | `airflow-webserver.out` | Information regarding Webserver startup and shutdown. | X | X |
| Worker | `airflow-worker.err` | Error messages, Gunicorn workers, Broker connection, and task execution details. | O | O |
| Worker | `airflow-worker.log` | Empty if started via systemd. | X | X |
| Worker | `airflow-worker.out` | Connected Broker, Result Backend, and monitored queues. | X | X |

Files marked for rotation:
- `airflow-scheduler.out`
- `airflow-webserver.log`
- `airflow-scheduler.out`

### Configuration & Setup
1. Create Rotation Directory (as your own user): `mkdir /home/<user>/airflow/logs_rotate`
2. User `root`: `vi /etc/logrotate.d/airflow`
    ```bash
    # Note: The third node only contain airflow-worker.err
    /home/<user>/airflow/airflow-scheduler.out
    /home/<user>/airflow/airflow-webserver.log
    /home/<user>/airflow/airflow-worker.err {
        daily
        rotate 7
        dateext
        olddir /home/<user>/airflow/logs_rotate
        compress
        nomissingok
        notifempty
        copytruncate
    }
    ```
