"""NexusAI Talent OS — Intelligence routes (prosody + fraud).

Registered by orchestrator under prefix /api/v1/intelligence.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_staff
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Answer, Interview
from app.services.prosody_service import analyze_prosody, text_confidence
from app.services.fraud_service import (
    FraudEventRejected, record_fraud_event, fraud_summary, detect_audio_anomaly,
)

router = APIRouter()

_MAX_METADATA_BYTES = 4096


# ── inline schemas ──────────────────────────────────────────────────────────
class FraudEventBody(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    metadata: Optional[dict] = None

    @field_validator("metadata")
    @classmethod
    def _cap_metadata(cls, v: Optional[dict]) -> Optional[dict]:
        if v is not None:
            import json
            if len(json.dumps(v, default=str)) > _MAX_METADATA_BYTES:
                raise ValueError(f"metadata exceeds {_MAX_METADATA_BYTES} bytes")
        return v


class ProsodyEntry(BaseModel):
    answer_id: str
    question_text: Optional[str] = None
    round_type: Optional[str] = None
    confidence: Optional[float] = None
    emotion: Optional[str] = None
    prosody: dict


class ProsodyResponse(BaseModel):
    interview_id: str
    count: int
    avg_confidence: float
    dominant_emotion: Optional[str]
    timeline: list[ProsodyEntry]


# ── helpers ─────────────────────────────────────────────────────────────────
async def _get_interview(db: AsyncSession, interview_id: str,
                         org_id: Optional[str]) -> Interview:
    stmt = select(Interview).where(Interview.id == interview_id)
    if org_id:
        stmt = stmt.where(Interview.org_id == org_id)
    iv = await db.scalar(stmt)
    if iv is None:
        raise HTTPException(status_code=404, detail="interview not found")
    return iv


async def _load_answers(db: AsyncSession, interview_id: str,
                        org_id: Optional[str]) -> list[Answer]:
    stmt = select(Answer).where(Answer.interview_id == interview_id)
    if org_id:
        stmt = stmt.where(Answer.org_id == org_id)
    stmt = stmt.order_by(Answer.created_at)
    return list((await db.scalars(stmt)).all())


def _aggregate(entries: list[dict]) -> tuple[float, Optional[str]]:
    if not entries:
        return 0.0, None
    confs = [e["confidence"] for e in entries if e.get("confidence") is not None]
    avg = round(sum(confs) / len(confs), 3) if confs else 0.0
    emotions: dict[str, int] = {}
    for e in entries:
        em = e.get("emotion")
        if em:
            emotions[em] = emotions.get(em, 0) + 1
    dominant = max(emotions, key=emotions.get) if emotions else None
    return avg, dominant


# ── routes ──────────────────────────────────────────────────────────────────
@router.get("/{interview_id}/prosody", response_model=ProsodyResponse)
async def get_prosody(interview_id: str, request: Request,
                      db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    await _get_interview(db, interview_id, org_id)
    answers = await _load_answers(db, interview_id, org_id)

    timeline: list[ProsodyEntry] = []
    flat: list[dict] = []
    for a in answers:
        stored = (a.ml_signals or {}).get("prosody") if a.ml_signals else None
        if not stored:
            stored = text_confidence(a.answer_text or "", a.audio_duration_seconds)
        flat.append(stored)
        timeline.append(ProsodyEntry(
            answer_id=a.id,
            question_text=a.question_text,
            round_type=a.round_type,
            confidence=stored.get("confidence"),
            emotion=stored.get("emotion"),
            prosody=stored,
        ))

    avg, dominant = _aggregate(flat)
    return ProsodyResponse(
        interview_id=interview_id, count=len(timeline),
        avg_confidence=avg, dominant_emotion=dominant, timeline=timeline,
    )


@router.post("/{interview_id}/analyze", dependencies=[Depends(require_staff)])
async def analyze_interview(interview_id: str, request: Request,
                            db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    await _get_interview(db, interview_id, org_id)
    answers = await _load_answers(db, interview_id, org_id)

    updated = 0
    flat: list[dict] = []
    for a in answers:
        audio = None
        if a.audio_s3_key and settings.PROSODY_MODEL == "wav2vec2":
            audio = await _try_load_audio(a.audio_s3_key)
        prosody = await analyze_prosody(audio, a.answer_text or "",
                                        a.audio_duration_seconds)
        signals = dict(a.ml_signals or {})
        signals["prosody"] = prosody
        a.ml_signals = signals
        a.confidence_score = prosody.get("confidence")
        flat.append(prosody)
        updated += 1

    await db.commit()
    avg, dominant = _aggregate(flat)
    return {
        "interview_id": interview_id,
        "answers_analyzed": updated,
        "avg_confidence": avg,
        "dominant_emotion": dominant,
        "method": settings.PROSODY_MODEL,
    }


@router.post("/{interview_id}/fraud-event")
async def fraud_event(interview_id: str, body: FraudEventBody, request: Request,
                      db: AsyncSession = Depends(get_db)):
    # candidate-facing: org_id may be None → look up without org filter
    org_id = getattr(request.state, "org_id", None)
    await _get_interview(db, interview_id, org_id)
    try:
        return await record_fraud_event(db, interview_id, body.event_type,
                                        body.metadata)
    except FraudEventRejected as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{interview_id}/fraud-summary")
async def get_fraud_summary(interview_id: str, request: Request,
                            db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    await _get_interview(db, interview_id, org_id)
    try:
        return await fraud_summary(db, interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _try_load_audio(s3_key: str) -> Optional[bytes]:
    """Best-effort S3 fetch; returns None if deps/credentials unavailable."""
    try:
        import asyncio
        import boto3  # type: ignore

        def _fetch() -> bytes:
            kwargs = {"region_name": settings.AWS_REGION}
            if settings.R2_ENDPOINT_URL:
                kwargs["endpoint_url"] = settings.R2_ENDPOINT_URL
            client = boto3.client("s3", **kwargs)
            obj = client.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
            return obj["Body"].read()

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)
    except Exception:
        return None
