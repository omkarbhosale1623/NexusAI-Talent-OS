"""
NexusAI Talent OS — lightweight Kafka consumer (no Spark required).

A pure-Python aiokafka consumer that subscribes to the `nexusai.*` topics and
maintains rolling, in-memory aggregates, periodically printing them (and
optionally upserting to Postgres). Use this when you want the streaming
pipeline without a full Spark cluster — e.g. local dev or small deployments.

Run:
    python pipeline/kafka_consumer.py

Env:
    KAFKA_BOOTSTRAP_SERVERS     default localhost:9092
    KAFKA_TOPIC_PREFIX          default nexusai
    KAFKA_DLQ_TOPIC             default nexusai.deadletter
    KAFKA_CONSUMER_MAX_RETRIES  default 3
    KAFKA_SCHEMA_VERSION        default 1   (the version this consumer speaks)
    FLUSH_SECONDS               default 30
"""
import asyncio
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nexusai.pipeline")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
PREFIX = os.getenv("KAFKA_TOPIC_PREFIX", "nexusai")
DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "nexusai.deadletter")
MAX_RETRIES = int(os.getenv("KAFKA_CONSUMER_MAX_RETRIES", "3"))
SUPPORTED_SCHEMA_VERSION = int(os.getenv("KAFKA_SCHEMA_VERSION", "1"))
FLUSH_SECONDS = int(os.getenv("FLUSH_SECONDS", "30"))

# org_id|job_id -> {"n": int, "score_sum": float}
_eval_agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "score_sum": 0.0})
_event_counts: dict[str, int] = defaultdict(int)


def _handle(event: dict) -> None:
    # Honour the versioned envelope: warn on unknown versions but still
    # process them as v1 (forward-compatible top-level shape).
    version = event.get("schema_version", 1)
    if version != SUPPORTED_SCHEMA_VERSION:
        logger.warning(
            "unknown schema_version=%s (supported=%s); processing as v1",
            version, SUPPORTED_SCHEMA_VERSION,
        )
    et = event.get("event_type", "unknown")
    _event_counts[et] += 1
    if et == "evaluation_created":
        p = event.get("payload", {})
        key = f"{p.get('org_id')}|{p.get('job_id')}"
        a = _eval_agg[key]
        a["n"] += 1
        a["score_sum"] += float(p.get("overall_score") or 0)


def _snapshot() -> dict:
    return {
        "ts": datetime.utcnow().isoformat(),
        "event_counts": dict(_event_counts),
        "avg_score_by_org_job": {
            k: round(v["score_sum"] / v["n"], 1)
            for k, v in _eval_agg.items() if v["n"]
        },
    }


async def _flusher() -> None:
    while True:
        await asyncio.sleep(FLUSH_SECONDS)
        logger.info("aggregate snapshot: %s", json.dumps(_snapshot()))


async def _to_dlq(producer, msg, reason: str) -> None:
    """Best-effort dead-letter of the raw message. Never raises."""
    try:
        envelope = {
            "reason": reason,
            "source_topic": msg.topic,
            "source_partition": msg.partition,
            "source_offset": msg.offset,
            "key": msg.key.decode() if msg.key else None,
            "value": msg.value,            # already-deserialized dict
            "dead_lettered_at": datetime.utcnow().isoformat(),
        }
        await producer.send_and_wait(DLQ_TOPIC, envelope, key=msg.key)
        logger.error("dead-lettered offset=%s partition=%s -> %s (%s)",
                     msg.offset, msg.partition, DLQ_TOPIC, reason)
    except Exception as exc:
        logger.error("DLQ send failed for offset=%s: %s", msg.offset, exc)


async def _process_with_retry(producer, msg) -> None:
    """Handle one message with bounded retries; dead-letter on exhaustion.

    Always returns (offset will be committed by the caller) so the consumer
    never stalls on a single poison message.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _handle(msg.value)
            return
        except Exception as exc:  # transient or poison message
            last_exc = exc
            logger.warning("handle failed (attempt %s/%s) offset=%s: %s",
                           attempt, MAX_RETRIES, msg.offset, exc)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(min(2 ** (attempt - 1), 10))  # backoff
    await _to_dlq(producer, msg, reason=str(last_exc))


async def main() -> None:
    try:
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    except ImportError:
        raise SystemExit("aiokafka not installed — pip install aiokafka")

    consumer = AIOKafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        value_deserializer=lambda b: json.loads(b.decode()),
        auto_offset_reset="latest",
        group_id="nexusai-pipeline",
        enable_auto_commit=False,          # manual commit after handle/DLQ
    )
    # idempotent producer for the dead-letter topic
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, default=str).encode(),
        enable_idempotence=True,
        acks="all",
    )
    # subscribe by pattern to catch every nexusai.<event_type> topic
    consumer.subscribe(pattern=re.compile(rf"{re.escape(PREFIX)}\..*"))
    await consumer.start()
    await producer.start()
    logger.info("consuming %s.* from %s (DLQ=%s, max_retries=%s)",
                PREFIX, BOOTSTRAP, DLQ_TOPIC, MAX_RETRIES)
    flusher = asyncio.create_task(_flusher())
    try:
        async for msg in consumer:
            if msg.topic == DLQ_TOPIC:
                await consumer.commit()    # don't reprocess the DLQ itself
                continue
            await _process_with_retry(producer, msg)
            # Commit only after the message is handled or dead-lettered, so a
            # crash mid-handle reprocesses rather than silently dropping.
            await consumer.commit()
    finally:
        flusher.cancel()
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
