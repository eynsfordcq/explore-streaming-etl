kafka-consumer-start:
	docker exec -it --user=root explore-streaming-etl-kafka-1 /opt/bitnami/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic users

start-python-interactive-container:
	docker run --rm -it -v ./:/app --network explore-streaming-etl_stream-etl python:3.12 /bin/bash