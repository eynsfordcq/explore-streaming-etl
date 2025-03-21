from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from pyspark.sql.functions import from_json, col

kafka_server = "kafka:9092"
kafka_topic = "users"
output_directory = "/app/tmp/output/"
checkpoint_directory = "/app/tmp/checkpoint/"

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

def read_stream_df():
    df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_server) \
    .option("subscribe", kafka_topic) \
    .load()
    return df 

def transform_stream_df(df: DataFrame):
    schema = StructType([
        StructField("name", StringType()),
        StructField("email", StringType()),
        StructField("gender", StringType()),
        StructField("address", StringType()),
        StructField("city", StringType()),
        StructField("nation", StringType()),
        StructField("zip", StringType()),
        StructField("latitude", DoubleType()),
        StructField("longitude", DoubleType())
    ])
    
    transformed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")
    return transformed_df

def write_stream_df(df):
    query = df.writeStream \
        .format("csv") \
        .outputMode("append") \
        .option("path", "s3a://users/output/") \
        .option("checkpointLocation", "s3a://users/checkpoints/") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    df = read_stream_df()
    if df:
        df = transform_stream_df(df)
        write_stream_df(df)