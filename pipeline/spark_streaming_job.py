"""
NexusAI Talent OS — Spark Structured Streaming analytics job.

Consumes evaluation/interview events from Kafka (produced by the API via
`app.services.warehouse_service.stream_event`), computes rolling aggregates,
and writes them to a sink (console by default; parquet or JDBC/Postgres
optional via env vars).

Run (inside the spark image, see Dockerfile):
    spark-submit \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
      pipeline/spark_streaming_job.py

Env:
    KAFKA_BOOTSTRAP_SERVERS   default kafka:9092
    KAFKA_TOPIC_PATTERN       default nexusai\\..*   (subscribePattern)
    SINK                      console | parquet | jdbc   (default console)
    PARQUET_PATH              default /data/warehouse
    JDBC_URL / JDBC_TABLE / JDBC_USER / JDBC_PASSWORD   (for SINK=jdbc)
    CHECKPOINT_DIR            default /tmp/nexusai-spark-checkpoint
"""
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, window
from pyspark.sql.types import (
    DoubleType, IntegerType, StringType, StructField, StructType,
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_PATTERN = os.getenv("KAFKA_TOPIC_PATTERN", r"nexusai\..*")
SINK = os.getenv("SINK", "console")
PARQUET_PATH = os.getenv("PARQUET_PATH", "/data/warehouse")
CHECKPOINT_DIR = os.getenv("CHECKPOINT_DIR", "/tmp/nexusai-spark-checkpoint")

# Versioned, self-describing envelope produced by warehouse_service.stream_event
EVENT_SCHEMA = StructType([
    StructField("schema_version", IntegerType()),
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("ts", StringType()),
    StructField("producer", StringType()),
    StructField("payload", StructType([
        StructField("interview_id", StringType()),
        StructField("org_id", StringType()),
        StructField("job_id", StringType()),
        StructField("candidate_id", StringType()),
        StructField("overall_score", DoubleType()),
        StructField("recommendation", StringType()),
        StructField("created_at", StringType()),
    ])),
])


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("nexusai-talent-analytics")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def main() -> None:
    spark = build_session()
    spark.sparkContext.setLogLevel("WARN")

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP)
        .option("subscribePattern", TOPIC_PATTERN)
        .option("startingOffsets", "latest")
        .load()
    )

    events = (
        raw.select(from_json(col("value").cast("string"), EVENT_SCHEMA).alias("e"))
        .select("e.event_type", "e.ts", "e.payload.*")
        .withColumn("event_time", to_timestamp(col("ts")))
    )

    # Rolling 1-hour aggregates of evaluation scores per org + job.
    evals = events.filter(col("event_type") == "evaluation_created")
    agg = (
        evals.withWatermark("event_time", "2 hours")
        .groupBy(window(col("event_time"), "1 hour"), col("org_id"), col("job_id"))
        .agg(
            {"overall_score": "avg", "interview_id": "count"},
        )
        .withColumnRenamed("avg(overall_score)", "avg_score")
        .withColumnRenamed("count(interview_id)", "evaluations")
    )

    if SINK == "parquet":
        query = (
            agg.writeStream.outputMode("append").format("parquet")
            .option("path", PARQUET_PATH)
            .option("checkpointLocation", CHECKPOINT_DIR)
            .start()
        )
    elif SINK == "jdbc":
        jdbc_url = os.environ["JDBC_URL"]
        table = os.getenv("JDBC_TABLE", "analytics_eval_hourly")

        def _write(batch_df, _bid):
            (batch_df.write.format("jdbc")
                .option("url", jdbc_url)
                .option("dbtable", table)
                .option("user", os.getenv("JDBC_USER", "nexusai"))
                .option("password", os.getenv("JDBC_PASSWORD", "nexusai"))
                .mode("append").save())

        query = (
            agg.writeStream.outputMode("update")
            .option("checkpointLocation", CHECKPOINT_DIR)
            .foreachBatch(_write).start()
        )
    else:  # console
        query = (
            agg.writeStream.outputMode("complete").format("console")
            .option("truncate", "false")
            .option("checkpointLocation", CHECKPOINT_DIR)
            .start()
        )

    query.awaitTermination()


if __name__ == "__main__":
    main()
