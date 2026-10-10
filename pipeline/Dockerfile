# Spark Structured Streaming job image for the NexusAI Talent OS analytics pipeline.
FROM bitnami/spark:3.5.1

USER root
WORKDIR /opt/pipeline
COPY spark_streaming_job.py kafka_consumer.py ./

# Pull the Kafka SQL connector at build time so spark-submit runs offline.
ENV SPARK_KAFKA_PKG=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1

ENTRYPOINT ["/opt/bitnami/spark/bin/spark-submit", \
  "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1", \
  "/opt/pipeline/spark_streaming_job.py"]
