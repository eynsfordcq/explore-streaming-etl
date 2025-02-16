import time
import requests
from kafka import KafkaProducer
from models.users import Users
from configs import config

def fetch_random_user() -> Users:
    response = requests.get(config.random_user_url)
    res = response.json().get("results")[0]
    return Users(
        name=f'{res["name"]["first"]} {res["name"]["last"]}',
        email=res["email"],
        gender=res["gender"],
        address=f'{res["location"]["street"]["number"]}, {res["location"]["street"]["name"]}',
        city=res["location"]["city"],
        nation=res["location"]["country"],
        zip=str(res["location"]["postcode"]),
        latitude=res["location"]["coordinates"]["latitude"],
        longitude=res["location"]["coordinates"]["longitude"]
    )

def publish_to_kafka(producer: KafkaProducer, topic: str, data: Users):
    data = data.model_dump_json().encode("utf-8")
    future = producer.send(topic, data)
    record_metadata = future.get(timeout=5)

    print("Topic:", record_metadata.topic)
    print("Partition:", record_metadata.partition)
    print("Offset:", record_metadata.offset)

if __name__ == "__main__":
    producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap_servers)

    for i in range(config.number_of_runs):
        user = fetch_random_user()
        publish_to_kafka(producer, config.kafka_topic, user)
        time.sleep(config.time_delay)