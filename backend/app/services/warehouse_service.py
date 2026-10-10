"""BigQuery analytics warehouse + Kafka event stream.

All optional deps (google-cloud-bigquery, aiokafka) are imported lazily and
every entry point degrades gracefully — nothing raises on missing backends.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── lazy optional deps ───────────────────────────────────────────────────────
try:
    from google.cloud import bigquery  # type: ignore
    _BIGQUERY = True
except ImportError:  # pragma: no cover
    bigquery = None  # type: ignore
    _BIGQUERY = False

try:
    from aiokafka import AIOKafkaProducer  # type: ignore
    _KAFKA = True
except ImportError:  # pragma: no cover
    AIOKafkaProducer = None  # type: ignore
    _KAFKA = False


# ── table names + event schemas ──────────────────────────────────────────────
TABLE_INTERVIEWS = "interviews"
TABLE_EVALUATIONS = "evaluations"
TABLE_EVENTS = "events"

EVENT_SCHEMAS: Dict[str, List[str]] = {
    "interviews": ["interview_id", "org_id", "job_id", "candidate_id", "status", "created_at"],
    "evaluations": ["interview_id", "org_id", "job_id", "overall_score",
                    "recommendation", "created_at"],
    "events": ["event_type", "org_id", "payload", "ts"],
}

# ── module-level lazy kafka producer ─────────────────────────────────────────
_producer: Optional["AIOKafkaProducer"] = None
_producer_lock = asyncio.Lock()


def _kafka_live() -> bool:
    return bool(settings.FEATURE_KAFKA) and _KAFKA


def _bigquery_live() -> bool:
    return bool(settings.FEATURE_WAREHOUSE) and _BIGQUERY and bool(settings.BIGQUERY_PROJECT)


def _key_serializer(k: Optional[str]) -> Optional[bytes]:
    return k.encode() if k is not None else None


async def _get_producer() -> Optional["AIOKafkaProducer"]:
    global _producer
    if not _kafka_live():
        return None
    if _producer is not None:
        return _producer
    async with _producer_lock:
        if _producer is None:
            try:
                p = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v, default=str).encode(),
                    key_serializer=_key_serializer,
                    # ── durability / idempotence ──────────────────────────────
                    enable_idempotence=True,   # no dup on producer retry
                    acks="all",                # wait for all in-sync replicas
                    max_batch_size=64 * 1024,  # 64 KiB batches
                    request_timeout_ms=15_000,
                )
                await p.start()
                _producer = p
            except Exception as exc:  # never raise
                logger.warning(f"kafka producer init failed: {exc}")
                _producer = None
    return _producer


# ── event envelope ───────────────────────────────────────────────────────────
def _build_envelope(event_type: str, payload: Dict) -> Dict[str, Any]:
    """Versioned, self-describing event envelope.

    Keeps top-level `event_type`/`ts`/`payload` so the existing Spark schema
    still parses, while adding `schema_version`/`event_id`/`producer`.
    """
    return {
        "schema_version": settings.KAFKA_SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "event_type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "producer": "nexusai-api",
        "payload": payload,
    }


# ── event stream ─────────────────────────────────────────────────────────────
async def stream_event(event_type: str, payload: Dict) -> Dict:
    """Produce an event to Kafka if enabled; always also no-op-logs. Never raises."""
    topic = f"{settings.KAFKA_TOPIC_PREFIX}.{event_type}"
    record = _build_envelope(event_type, payload)
    # Partition by tenant so a single org's events stay ordered.
    key = payload.get("org_id") if isinstance(payload, dict) else None
    producer = await _get_producer()
    if producer is not None:
        try:
            await producer.send_and_wait(topic, record, key=key)
            return {"ok": True, "topic": topic, "transport": "kafka",
                    "event_id": record["event_id"]}
        except Exception as exc:  # never raise
            logger.warning(f"kafka send failed ({topic}): {exc}")
            if await _send_to_dlq(producer, record):
                return {"ok": False, "topic": topic, "transport": "dlq",
                        "event_id": record["event_id"], "reason": str(exc)}
    logger.info(f"[event] {topic} {json.dumps(payload, default=str)[:500]}")
    return {"ok": False, "topic": topic, "transport": "log",
            "reason": "kafka disabled or unavailable"}


async def _send_to_dlq(producer: "AIOKafkaProducer", record: Dict) -> bool:
    """Best-effort write of a failed record to the dead-letter topic. Never raises."""
    try:
        key = record.get("payload", {}).get("org_id") if isinstance(
            record.get("payload"), dict) else None
        await producer.send_and_wait(settings.KAFKA_DLQ_TOPIC, record, key=key)
        logger.warning(f"event routed to DLQ {settings.KAFKA_DLQ_TOPIC} "
                       f"(event_id={record.get('event_id')})")
        return True
    except Exception as exc:  # never raise
        logger.warning(f"kafka DLQ send failed: {exc}")
        return False


async def close_producer() -> None:
    """Flush + stop the shared producer on shutdown. Idempotent, never raises."""
    global _producer
    p = _producer
    _producer = None
    if p is not None:
        try:
            await p.stop()
        except Exception as exc:  # never raise
            logger.warning(f"kafka producer close failed: {exc}")


def producer_health() -> Dict[str, Any]:
    """Lightweight, non-blocking producer health snapshot."""
    return {
        "kafka_enabled": bool(settings.FEATURE_KAFKA),
        "lib": _KAFKA,
        "live": _kafka_live(),
        "producer_started": _producer is not None,
        "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "schema_version": settings.KAFKA_SCHEMA_VERSION,
        "dlq_topic": settings.KAFKA_DLQ_TOPIC,
    }


# ── warehouse export ─────────────────────────────────────────────────────────
async def export_evaluation(row: Dict) -> Dict:
    """Insert one evaluation row into BigQuery, else {ok:False, reason}."""
    if not _bigquery_live():
        return {"ok": False, "reason": "warehouse disabled or bigquery unavailable"}
    table = f"{settings.BIGQUERY_PROJECT}.{settings.BIGQUERY_DATASET}.{TABLE_EVALUATIONS}"

    def _insert() -> List:
        client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
        return client.insert_rows_json(table, [row])

    try:
        errors = await asyncio.get_event_loop().run_in_executor(None, _insert)
        if errors:
            return {"ok": False, "reason": str(errors)}
        return {"ok": True, "table": table}
    except Exception as exc:
        logger.warning(f"bigquery export failed: {exc}")
        return {"ok": False, "reason": str(exc)}


# ── presets ──────────────────────────────────────────────────────────────────
_PRESETS = {
    "avg_score_by_job": "avg_score_by_job",
    "hires_over_time": "hires_over_time",
}


async def query_metrics(org_id: Optional[str], sql_or_preset: str) -> Dict:
    """Run an aggregate preset against BigQuery if live, else Postgres fallback."""
    preset = sql_or_preset if sql_or_preset in _PRESETS else "avg_score_by_job"
    if _bigquery_live():
        try:
            rows = await _query_bigquery(org_id, preset)
            return {"preset": preset, "source": "bigquery", "rows": rows}
        except Exception as exc:
            logger.warning(f"bigquery query failed, falling back to postgres: {exc}")
    rows = await _query_postgres(org_id, preset)
    return {"preset": preset, "source": "postgres", "rows": rows}


async def _query_bigquery(org_id: Optional[str], preset: str) -> List[Dict]:
    dataset = f"{settings.BIGQUERY_PROJECT}.{settings.BIGQUERY_DATASET}"
    where = f"WHERE org_id = '{org_id}'" if org_id else ""
    if preset == "hires_over_time":
        sql = (
            f"SELECT DATE(created_at) AS day, COUNT(*) AS hires "
            f"FROM `{dataset}.{TABLE_EVALUATIONS}` {where} "
            f"{'AND' if where else 'WHERE'} recommendation IN ('Strong Hire','Hire') "
            f"GROUP BY day ORDER BY day"
        )
    else:  # avg_score_by_job
        sql = (
            f"SELECT job_id, AVG(overall_score) AS avg_score, COUNT(*) AS n "
            f"FROM `{dataset}.{TABLE_EVALUATIONS}` {where} "
            f"GROUP BY job_id ORDER BY avg_score DESC"
        )

    def _run() -> List[Dict]:
        client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
        return [dict(r) for r in client.query(sql).result()]

    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def _query_postgres(org_id: Optional[str], preset: str) -> List[Dict]:
    from sqlalchemy import select, func, and_
    from app.core.database import AsyncSessionLocal
    from app.models.models import Evaluation, Interview

    async with AsyncSessionLocal() as db:
        if preset == "hires_over_time":
            day = func.date(Evaluation.created_at)
            stmt = select(day.label("day"), func.count().label("hires")).where(
                Evaluation.recommendation.in_(["Strong Hire", "Hire"]))
            if org_id:
                stmt = stmt.where(Evaluation.org_id == org_id)
            stmt = stmt.group_by(day).order_by(day)
            res = await db.execute(stmt)
            return [{"day": str(r.day), "hires": int(r.hires)} for r in res.all()]
        else:  # avg_score_by_job
            stmt = select(
                Interview.job_id.label("job_id"),
                func.avg(Evaluation.overall_score).label("avg_score"),
                func.count().label("n"),
            ).join(Interview, Interview.id == Evaluation.interview_id)
            if org_id:
                stmt = stmt.where(Evaluation.org_id == org_id)
            stmt = stmt.group_by(Interview.job_id).order_by(
                func.avg(Evaluation.overall_score).desc())
            res = await db.execute(stmt)
            return [{"job_id": r.job_id,
                     "avg_score": round(float(r.avg_score or 0), 2),
                     "n": int(r.n)} for r in res.all()]


def warehouse_status() -> Dict:
    return {
        "kafka": {"enabled": bool(settings.FEATURE_KAFKA), "lib": _KAFKA,
                  "live": _kafka_live()},
        "bigquery": {"enabled": bool(settings.FEATURE_WAREHOUSE), "lib": _BIGQUERY,
                     "project": bool(settings.BIGQUERY_PROJECT), "live": _bigquery_live()},
        "tables": [TABLE_INTERVIEWS, TABLE_EVALUATIONS, TABLE_EVENTS],
    }
