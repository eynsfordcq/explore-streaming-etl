# explore-streaming-etl

## Overview

The goal of this project is to explore how spark streaming works. It is inspired by this project [github](https://github.com/simardeep1792/Data-Engineering-Streaming-Project).
Overview of the ETL process:
- A producer generates random user and post it to kafka. The producer is scheduled using airflow and runs every minute, for each run, about 10 users are generated, 1 per second.
- A spark streaming ingestion script listens to the kafka topic. Transforms it, and store it in a csv file in S3 (minio here).

## Breakdown of Components

### Kafka

- This is the message queue where the "producer" will publish to and where the "consumer" will read from.
- Recent version of introduces a "kraft mode" which replaces zookeeper for metadata management.
- Not sure but general idea is:
    - 9093 is used the controller, like quorum voting, metadata management
	- 9092 is the broker, used by producers, consumers or clients

```yaml
  kafka:
    image: bitnami/kafka:latest
    environment:
      KAFKA_CFG_NODE_ID: 1
      KAFKA_CFG_PROCESS_ROLES: broker,controller
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: "1@kafka:9093"
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE: "true"
    ports:
      - "9092:9092"
      - "9093:9093"
```

### Producer Script

- This is a simple python script that retrieve random user from `https://randomuser.me` 
- Then, it publishes the results to a kafka topic
- Nothing really fancy, the only thing worth mentioning is the KafkaProducer
	- the bootstrap_servers should be the kafka brokers port, since it's sending message to it
	- if you have more brokers or nodes, you'd config something like `kafka1:9092,kafka2:9092,kafka3:9092`, if one goes down, it will try to send the message to the following broker.

### Spark Streaming Ingestion

- This script reads stream from the kafka topic, similarly, we have to configure bootstrap.servers, and the kafka topic.

```python
# read 
    df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_server) \
    .option("subscribe", kafka_topic) \
    .load()
    return df 
```

- Then, we need to do some transformation
	- When it reads from kafka, the message is binary
	- We need to first cast as string, this will give us the raw json in a long string
	- Then, convert the string into json using from_json
	- Then, select it to make it table-like

```python
# transform
    transformed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")
```

- Finally, we need to write it to s3 (minio)
- We use the trigger to specify the processingTime, which means it will get trigger every 10 seconds. This is to avoid every new row being written as one file.
- `awaitTermination`  blocks the process until stopped by external signal like keyboard interrupt, otherwise, it will keep running.

```python
query = df.writeStream \
	.format("csv") \
	.outputMode("append") \
	.option("path", "s3a://users/output/") \
	.option("checkpointLocation", "s3a://users/checkpoints/") \
	.trigger(processingTime="10 seconds") \
	.start()

query.awaitTermination()
```

- Because we are writing to s3, we need to configure it 
	- `spark.hadoop.fs.s3a.path.style.acces`: instead of accessing the bucket via http://bucket-name.s3.amazonaws.com, you would access it via http://s3.amazonaws.com/bucket-name. It's important because we are using minio, which does not support the default virtual-hosted style for bucket access.
	- `spark.hadoop.fs.s3a.impl`: specifies the implementation class for the S3A filesystem. 

```sh
# basic configurations as you would have expected, endpoint, access key, secret key
spark = SparkSession \
    .builder \
    .master("local[*]") \
    .appName("SparkIngestion") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minio") \
    .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()
```

- To make the Spark script run, we need 3 packages 
	- `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1`
	- `aws-java-sdk-bundle-1.12.262.jar`
	- `hadoop-aws-3.3.4.jar`
	- The bottom 2 for s3 is already included in the bitnami image
    - For the kafka, we simply specify `--packages` when submitting the job and let ivy2 download it for us

```bash
# the s3 packages are included in $SPARK_HOME/jars
/opt/bitnami/spark/jars$ ls -l | grep aws 
-rw-rw-r-- 1 1001 root 280645251 Dec 21 00:32 aws-java-sdk-bundle-1.12.262.jar
-rw-rw-r-- 1 1001 root    962685 Dec 21 00:31 hadoop-aws-3.3.4.jar

# spark submit with packages 
spark-submit \
	--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
	/app/spark/ingestion.py
```

### MinIO

- This is the S3-compatible storage that we will use to store our data
	- 9000 is the api port
	- 9001 is the web-ui
- The root user and password can be used as access key and secret key respectively

```yaml
  minio:
    image: quay.io/minio/minio
    environment:
      - MINIO_ROOT_USER=minio
      - MINIO_ROOT_PASSWORD=minio123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    command: ["server", "/data", "--console-address", ":9001"]
```

### Airflow

- For airflow, we will just use LocalExecutor instead of the CeleryExecutor shown in most examples
- Most of the configurations are default from [bitnami docker hub](https://hub.docker.com/r/bitnami/airflow)
- The only things to note:
	- We can mount the requirements.txt at a specified directory and it will auto install the packages during startup (not sure if this is bitnami image feature)
	- Changed it to LocalExecutor, therefore we don't need redis and worker node anymore
	- `AIRFLOW_SECRET_KEY`: Apparently when we don't set this, we can't view the log of each run, I think it can be anything, I generated it with openssl rand

```yaml
  postgresql:
    image: docker.io/bitnami/postgresql:latest
    ports:
      - '5432:5432'
    volumes:
      - 'postgresql_data:/bitnami/postgresql'
    environment:
      - POSTGRESQL_DATABASE=bitnami_airflow
      - POSTGRESQL_USERNAME=bn_airflow
      - POSTGRESQL_PASSWORD=bitnami1
      # ALLOW_EMPTY_PASSWORD is recommended only for development.
      - ALLOW_EMPTY_PASSWORD=yes
  
  airflow-scheduler:
    image: docker.io/bitnami/airflow:2
    environment:
      - AIRFLOW_COMPONENT_TYPE=scheduler
      - AIRFLOW_DATABASE_NAME=bitnami_airflow
      - AIRFLOW_DATABASE_USERNAME=bn_airflow
      - AIRFLOW_DATABASE_PASSWORD=bitnami1
      - AIRFLOW_EXECUTOR=LocalExecutor
      - AIRFLOW_WEBSERVER_HOST=airflow
      - AIRFLOW_LOAD_EXAMPLES=no
      - AIRFLOW_SECRET_KEY=0IM8qEioXkoh7xT5
    volumes:
      - ./dags:/opt/bitnami/airflow/dags
      - ./producer:/app/producer
      - ./producer/requirements.txt:/bitnami/python/requirements.txt

  airflow:
    image: docker.io/bitnami/airflow:2
    environment:
      - AIRFLOW_DATABASE_NAME=bitnami_airflow
      - AIRFLOW_DATABASE_USERNAME=bn_airflow
      - AIRFLOW_DATABASE_PASSWORD=bitnami1
      - AIRFLOW_EXECUTOR=LocalExecutor
      - AIRFLOW_USERNAME=airflow
      - AIRFLOW_PASSWORD=airflow
      - AIRFLOW_LOAD_EXAMPLES=no
      - AIRFLOW_SECRET_KEY=0IM8qEioXkoh7xT5
    ports:
      - '8080:8080'
    volumes:
      - ./dags:/opt/bitnami/airflow/dags
      - ./producer:/app/producer
      - ./producer/requirements.txt:/bitnami/python/requirements.txt
```

- Dag
	- For the dag, it's the most simple dag that I can think of 
	- I simply use a bash operator, to run the script that I mounted in /app. The packages are handled by mounting the `requirements.txt` (see above)
