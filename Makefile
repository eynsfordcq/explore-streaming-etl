kafka-consumer-start:
	docker exec -it --user=root explore-streaming-etl-kafka-1 /opt/bitnami/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic users

start-python-interactive-container:
	docker run --rm -it -v ./:/app --network stream-etl python:3.12 /bin/bash

spark-submit-streaming:
	docker exec -it explore-streaming-etl-spark-1 spark-submit \
		--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
		/app/spark/ingestion.py