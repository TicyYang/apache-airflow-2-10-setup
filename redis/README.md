# Redis 7.2.4 High-Availability (Sentinel) Setup

This guide demonstrates the deployment of a 3 node Redis Sentinel cluster (1 Master, 2 Slaves). Unless specified otherwise, all settings must be executed across all 3 nodes.

---

## Environment

- OS: Ubuntu Server 22.04 LTS
- Redis: 7.2.4

## Installation (All 3 Nodes)

Execute the following commands to install Redis and configure the environment:
```bash
# Download and install
wget https://github.com/redis/redis/archive/refs/tags/7.2.4.tar.gz
tar xf 7.2.4.tar.gz && cd redis-7.2.4/
make && sudo make PREFIX=/usr/local/redis install

# System Link
sudo ln -s /usr/local/redis/bin/redis-* /usr/bin/

# Create directories
sudo mkdir -p /data/redis/persist_data
sudo chown -R <user>:<user> /usr/local/redis /data

# Enable overcommit memory
echo 'vm.overcommit_memory=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```


## Configuration (All 3 Nodes)

1. Copy config:
    ```bash
    cp redis.conf /usr/local/redis/bin/
    cp sentinel.conf /usr/local/redis/bin/
    cd /usr/local/redis/bin/
    ```

2. Redis: `vi redis.conf`
    ```toml
    protected-mode no
    daemonize yes
    logfile "/data/redis-server.log"
    dir /data/redis/persist_data
    
    # For Slaves (Nodes 2 & 3) only:
    # replicaof <MASTER_IP> 6379
    ```

3. Redis Sentinel: `vi sentinel.conf`
    ```toml
    daemonize yes
    logfile "/data/sentinel.log"
    sentinel monitor mymaster <MASTER_IP> 6379 2
    sentinel down-after-milliseconds mymaster 10000
    sentinel failover-timeout mymaster 60000
    ```


## Run as a System Service (All 3 Nodes)
1. Examples can be found in the directory `systemd`.
    - `redis.service`
    - `redis-sentinel.service`

2. Reload system services: `systemctl daemon-reload`

3. Using the following commands to manage services:
    ```bash
    # Redis
    systemctl enable redis
    systemctl disable redis
    systemctl start redis
    systemctl stop redis
    systemctl status redis

    # Redis-Sentinel
    systemctl enable redis-sentinel
    systemctl disable redis-sentinel
    systemctl start redis-sentinel
    systemctl stop redis-sentinel
    systemctl status redis-sentinel
    ```


## Verification
- Check Replication: `redis-cli -p 6379 INFO REPLICATION`
- Check Sentinel: `redis-cli -p 26379 SENTINEL GET-MASTER-ADDR-BY-NAME mymaster`
- Benchmark: `redis-benchmark -n 100000`


## Security & Authentication
1. Redis: `vi /usr/local/redis/bin/redis.conf`
    ```toml
    # The authentication information required for a slave to connect to the master.
    # The slave sends "auth <username> <pass>" when connecting to the master.
    masteruser "airflow"
    masterauth "redis123"

    # Create ACL user, write below ###### SECURITY ######.
    # Define 'airflow' user with full access and encrypted payload
    user airflow on sanitize-payload ~* &* +@all >redis123
    
    # Password for default user
    requirepass "abc123"
    ```

2. Sentinel: `vi /usr/local/redis/bin/sentinel.conf`
    ```toml
    # The authentication information for Sentinel to connect to master.
    sentinel auth-pass mymaster redis123
    sentinel auth-user mymaster airflow

    # Create ACL user.
    # Both Sentinel's username & password and authentication information must be the same.
    user airflow on >sent123 sanitize-payload ~* &* +@all

    # The authentication information for Sentinels to connect to each other.
    # If using the "default" user, only the password needs to be declared.
    sentinel sentinel-user airflow
    sentinel sentinel-pass sent123

    requirepass "abc123"
    ```

3. Login
Once connected via redis-cli, use the following commands to authenticate:
```bash
# For user "airflow"
auth airflow redis123

# For default User
auth abc123
```


## Log Management (All 3 Nodes)

1. Create Rotation Directory (as your own user): `mkdir /data/redis_logs_rotate`
2. 使用者 `root`: `vi /etc/logrotate.d/redis`
    ```bash
    /data/redis-server.log
    /data/sentinel.log {
        daily
        rotate 7
        dateext
        olddir /data/redis_logs_rotate/
        compress
        nomissingok
        notifempty
        copytruncate
    }
    ```