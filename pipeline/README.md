# NexusAI Talent OS — Analytics Pipeline (Kafka → Spark)

Event-driven analytics pipeline. The API emits events through
`app.services.warehouse_service.stream_event(event_type, payload)`, which
produces JSON messages to Kafka topics named `nexusai.<event_type>`
(e.g. `nexusai.evaluation_created`, `nexusai.recruiter_feedback`).

## Event envelope (versioned)

Every message is a self-describing, versioned JSON envelope so consumers can
evolve independently of producers:

```json
{
  "schema_version": 1,
  "event_id": "0f1c2d…",        // uuid4 hex, unique per event
  "event_type": "evaluation_created",
  "ts": "2026-06-28T12:00:00+00:00",  // ISO-8601, UTC
  "producer": "nexusai-api",
  "payload": { "org_id": "…", "job_id": "…", "overall_score": 8.5, … }
}
```

- `schema_version` is `settings.KAFKA_SCHEMA_VERSION`. Consumers warn on an
  unknown version but still process it as v1 (top-level shape is stable).
- The top-level `event_type`/`ts`/`payload` keys are preserved so the Spark
  schema continues to parse older readers without change.

## Partitioning & ordering

Events are produced with a **partition key = `payload.org_id`**, so all events
for a single tenant land on the same partition and stay strictly ordered.

## Idempotent, durable producer

The API-side producer (`warehouse_service._get_producer`) is configured for
at-least-once-with-dedup delivery:

- `enable_idempotence=True` — no duplicates on internal producer retries
- `acks="all"` — wait for all in-sync replicas before acking
- bounded `request_timeout_ms` + batched `max_batch_size`

`stream_event` never raises (it is fire-and-forget on request paths). On a send
failure it best-effort writes the original record to the **dead-letter topic**
(`KAFKA_DLQ_TOPIC`, default `nexusai.deadletter`) and otherwise falls back to a
structured log line. `close_producer()` flushes + stops on shutdown and
`producer_health()` exposes a non-blocking status snapshot.

## Dead-letter queue & manual-commit consumer

`kafka_consumer.py` uses **manual offset commits**
(`enable_auto_commit=False`): an offset is committed only after the message is
successfully handled *or* dead-lettered, so a crash mid-handle reprocesses
rather than silently dropping.

- Each message is retried up to `KAFKA_CONSUMER_MAX_RETRIES` (default 3) with
  exponential backoff.
- On exhaustion the **raw message** (plus failure reason and source
  topic/partition/offset) is produced to `KAFKA_DLQ_TOPIC` via an idempotent
  producer, then the offset is committed so the consumer does not stall on a
  poison message.
- The consumer skips (and commits past) any messages on the DLQ topic itself.

Two consumers are provided:

| File | Use it when |
|---|---|
| `spark_streaming_job.py` | You want a real Spark Structured Streaming job with windowed aggregates and a parquet/JDBC sink. |
| `kafka_consumer.py` | You want the streaming pipeline **without** Spark (pure-Python `aiokafka`, in-memory rolling aggregates). Good for dev / small deployments. |

## Enable the producer side

In `backend/.env`:

```bash
FEATURE_KAFKA=true
KAFKA_BOOTSTRAP_SERVERS=kafka:9092   # or localhost:9092 outside docker
KAFKA_TOPIC_PREFIX=nexusai
```

With `FEATURE_KAFKA=false` (default) the API simply logs events and never
connects to Kafka — the rest of the platform is unaffected.

## Run with docker-compose

The optional `kafka`, `zookeeper`, and `spark_pipeline` services live in the
root `docker-compose.yml` under the `pipeline` profile:

```bash
docker-compose --profile pipeline up -d zookeeper kafka spark_pipeline
```

## Run the Spark job manually

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  pipeline/spark_streaming_job.py
```

Env knobs: `SINK=console|parquet|jdbc`, `PARQUET_PATH`, `JDBC_URL`/`JDBC_TABLE`,
`CHECKPOINT_DIR`. See the docstring at the top of `spark_streaming_job.py`.

## Run the lightweight consumer

```bash
pip install aiokafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python pipeline/kafka_consumer.py
```

## Status

This is a **production-leaning MVP**: the producer is wired into evaluation
completion and recruiter feedback; messages use a versioned, self-describing
envelope; the producer is idempotent + durable with DLQ-on-failure; and the
lightweight consumer does bounded per-message retry, dead-lettering, and manual
offset commits. The Spark job computes hourly average-score-by-job windows.

### Still needed for true production

- **Schema registry / Avro (or Protobuf)** — replace ad-hoc JSON + the integer
  `schema_version` with a registry-enforced contract and backward/forward
  compatibility checks. JSON-on-the-wire has no enforced schema today.
- **Exactly-once sink** — the Spark/consumer sinks are at-least-once. Use
  idempotent upserts (or Kafka transactions / Delta-style commit logs) for
  exactly-once end-to-end.
- **Partition sizing & autoscaling** — capacity-plan partitions per topic for
  throughput + tenant ordering, and size consumer instances/Spark executors to
  match. `org_id` keying can hot-spot large tenants; consider composite keys.
- **Monitoring & consumer-lag alerts** — export producer/consumer metrics,
  alert on consumer-group lag, DLQ volume, and producer error rate; add tracing.
- **DLQ reprocessing** — an operator tool to inspect/replay dead-lettered
  messages after a fix is deployed.
