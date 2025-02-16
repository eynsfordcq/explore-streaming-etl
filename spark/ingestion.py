from pyspark.sql import SparkSession

kafka_server = "kafka:19092"
kafka_topic = "users"
output_directory = "/app/tmp/output/"
checkpoint_directory = "/app/tmp/checkpoint/"

spark = SparkSession \
    .builder \
    .appName("SparkIngestion") \
    .getOrCreate()

def read_stream_df():
    df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_server) \
    .option("subscribe", kafka_topic) \
    .load()
    return df 

def write_stream_df(df):
    query = df.writeStream \
        .outputMode("append") \
        .format("csv") \
        .option("path", output_directory) \
        .option("checkpointLocation", checkpoint_directory) \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    df = read_stream_df()
    if df:
        write_stream_df(df)