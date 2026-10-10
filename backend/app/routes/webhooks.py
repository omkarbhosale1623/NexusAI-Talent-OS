"""NexusAI Talent OS — Webhooks (proctoring events from candidate browser)"""
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Interview, ProctoringEvent
from app.schemas.schemas import ProctoringEventRequest

router = APIRouter()

SEVERITY_MAP = {
    "FACE_ABSENT": "medium", "MULTIPLE_FACES": "high", "GAZE_AWAY": "low",
    "PHONE_DETECTED": "high", "TAB_SWITCH": "medium", "COPY_PASTE": "low",
    "BACKGROUND_VOICE": "medium",
}
RISK_DELTA = {"low": 0.05, "medium": 0.1, "high": 0.2, "critical": 0.4}

@router.post("/proctoring/{interview_id}")
async def receive_proctoring_event(
    interview_id: str, body: ProctoringEventRequest, db: AsyncSession = Depends(get_db),
):
    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if not iv: raise HTTPException(404, "Interview not found")
    severity = SEVERITY_MAP.get(body.event_type, "low")
    new_risk = min(1.0, iv.proctoring_risk_score + RISK_DELTA.get(severity, 0.05))

    db.add(ProctoringEvent(
        interview_id=interview_id, org_id=iv.org_id, event_type=body.event_type,
        severity=severity, confidence=body.confidence, event_metadata=body.metadata,
        timestamp=body.timestamp,
    ))
    iv.proctoring_risk_score = new_risk
    iv.proctoring_events_count = (iv.proctoring_events_count or 0) + 1
    await db.commit()
    return {"status": "recorded", "severity": severity, "risk_score": new_risk}

@router.post("/proctoring/{interview_id}/frame")
async def receive_video_frame(interview_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Analyze video frame for face/phone detection. Uses MediaPipe + YOLOv8n — no training needed."""
    if not settings.FEATURE_PROCTORING:
        return {"status": "disabled", "events_detected": 0}
    frame_b64 = body.get("frame", "")
    if not frame_b64: raise HTTPException(400, "No frame data")

    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if not iv: raise HTTPException(404, "Interview not found")

    try:
        from app.services.proctoring_service import frame_analyzer, update_session_risk
        frame_bytes = base64.b64decode(frame_b64)
        events = await frame_analyzer.analyze(frame_bytes, interview_id)
    except ImportError:
        events = []  # proctoring_service deps not installed — fail silently
    except Exception:
        events = []

    if events:
        for ev in events:
            db.add(ProctoringEvent(
                interview_id=interview_id, org_id=iv.org_id, event_type=ev["event_type"],
                severity=ev["severity"], confidence=ev.get("confidence"),
                event_metadata=ev.get("metadata", {}), timestamp=datetime.utcnow(),
            ))
        delta = sum(RISK_DELTA.get(e["severity"], 0.05) for e in events)
        iv.proctoring_risk_score = min(1.0, iv.proctoring_risk_score + delta)
        iv.proctoring_events_count = (iv.proctoring_events_count or 0) + len(events)
        await db.commit()

    return {"events_detected": len(events), "violations": [e["event_type"] for e in events]}

@router.get("/proctoring/{interview_id}/summary")
async def proctoring_summary(interview_id: str, db: AsyncSession = Depends(get_db)):
    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if not iv: raise HTTPException(404)
    from sqlalchemy import func
    events = (await db.scalars(
        select(ProctoringEvent).where(ProctoringEvent.interview_id == interview_id)
    )).all()
    by_type = {}
    for e in events:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
    risk = iv.proctoring_risk_score
    level = "low" if risk < settings.PROCTORING_RISK_LOW_THRESHOLD else \
            "medium" if risk < settings.PROCTORING_RISK_MEDIUM_THRESHOLD else \
            "high" if risk < settings.PROCTORING_RISK_HIGH_THRESHOLD else "critical"
    return {
        "total_events": len(events), "events_by_type": by_type,
        "risk_score": risk, "risk_level": level,
        "integrity_score": max(0, 100 - int(risk * 100)),
    }
