"""NexusAI Talent OS — Advanced fraud / integrity detection aggregator.

Persists proctoring events, maintains a clamped fraud_risk_score and a distinct
flag list on the Interview, and exposes a summary + audio-anomaly heuristic.
"""
from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Interview, ProctoringEvent

# event_type → risk weight (uses configured settings weights)
FRAUD_EVENT_WEIGHTS: dict[str, float] = {
    "tab_switch": settings.FRAUD_TAB_SWITCH_WEIGHT,
    "window_blur": settings.FRAUD_TAB_SWITCH_WEIGHT,
    "copy": settings.FRAUD_PASTE_WEIGHT * 0.5,
    "paste": settings.FRAUD_PASTE_WEIGHT,
    "multiple_faces": settings.FRAUD_MULTI_FACE_WEIGHT,
    "no_face": settings.FRAUD_MULTI_FACE_WEIGHT * 0.5,
    "phone_detected": settings.FRAUD_MULTI_FACE_WEIGHT,
    "gaze_away": settings.FRAUD_TAB_SWITCH_WEIGHT * 0.75,
    "audio_anomaly": settings.FRAUD_AUDIO_ANOMALY_WEIGHT,
    "voice_mismatch": settings.FRAUD_AUDIO_ANOMALY_WEIGHT * 1.5,
    "second_voice": settings.FRAUD_AUDIO_ANOMALY_WEIGHT * 2.0,
}

_RECOMMENDATIONS = {
    "low": "No significant integrity concerns. Proceed normally.",
    "medium": "Some integrity signals detected. Manual review recommended.",
    "high": "High fraud risk. Strong manual review required before any decision.",
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _severity_for(weight: float) -> str:
    if weight >= 0.18:
        return "high"
    if weight >= 0.10:
        return "medium"
    return "low"


def _risk_level(score: float) -> str:
    high = settings.FRAUD_HIGH_RISK_THRESHOLD
    if score >= high:
        return "high"
    if score >= high * 0.5:
        return "medium"
    return "low"


class FraudEventRejected(Exception):
    """Raised when a fraud event is invalid or not allowed in the current state."""


async def record_fraud_event(db: AsyncSession, interview_id: str,
                             event_type: str, metadata: dict | None) -> dict:
    """Persist a ProctoringEvent, recompute interview fraud score + flags.

    Candidate-facing input — event_type must be a known type and confidence is
    clamped to [0,1] so a crafted payload can neither inflate nor *reduce* the
    accumulated fraud score. Completed/cancelled interviews are immutable.
    """
    if event_type not in FRAUD_EVENT_WEIGHTS:
        raise FraudEventRejected(f"unknown event_type: {event_type}")

    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if iv is None:
        raise ValueError(f"interview not found: {interview_id}")
    if iv.status in ("completed", "evaluated", "cancelled", "no_show"):
        raise FraudEventRejected("interview is no longer accepting events")

    weight = FRAUD_EVENT_WEIGHTS[event_type]
    severity = _severity_for(weight)
    try:
        conf = float((metadata or {}).get("confidence", 1.0))
    except (TypeError, ValueError):
        conf = 1.0
    conf = _clamp(conf)

    evt = ProctoringEvent(
        interview_id=interview_id,
        org_id=iv.org_id,
        event_type=event_type,
        severity=severity,
        confidence=conf,
        event_metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
    )
    db.add(evt)

    # recompute clamped score (additive, weighted by confidence)
    new_score = _clamp((iv.fraud_risk_score or 0.0) + weight * conf)
    iv.fraud_risk_score = new_score

    flag = event_type
    flags = list(iv.fraud_flags or [])
    if flag not in flags:
        flags.append(flag)
        iv.fraud_flags = flags

    high_risk = new_score >= settings.FRAUD_HIGH_RISK_THRESHOLD
    await db.commit()

    return {
        "fraud_risk_score": round(new_score, 3),
        "severity": severity,
        "flag": flag,
        "high_risk": high_risk,
    }


async def fraud_summary(db: AsyncSession, interview_id: str) -> dict:
    """Aggregate counts + current risk level + recommendation."""
    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if iv is None:
        raise ValueError(f"interview not found: {interview_id}")

    rows = (await db.execute(
        select(ProctoringEvent.event_type, func.count())
        .where(ProctoringEvent.interview_id == interview_id)
        .group_by(ProctoringEvent.event_type)
    )).all()
    counts = {et: int(c) for et, c in rows}

    score = round(iv.fraud_risk_score or 0.0, 3)
    level = _risk_level(score)

    return {
        "interview_id": interview_id,
        "fraud_risk_score": score,
        "risk_level": level,
        "flags": list(iv.fraud_flags or []),
        "event_counts": counts,
        "total_events": sum(counts.values()),
        "high_risk_threshold": settings.FRAUD_HIGH_RISK_THRESHOLD,
        "recommendation": _RECOMMENDATIONS[level],
    }


def detect_audio_anomaly(prosody: dict, baseline: dict | None) -> dict:
    """Heuristic: large jumps vs a baseline answer suggest a second speaker /
    playback. Returns {anomaly, reason, score}."""
    if not prosody:
        return {"anomaly": False, "reason": "no_prosody", "score": 0.0}
    if not baseline:
        return {"anomaly": False, "reason": "no_baseline", "score": 0.0}

    def _g(d: dict, k: str) -> float:
        try:
            return float(d.get(k) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    pv_b = _g(baseline, "pitch_variability")
    pv_c = _g(prosody, "pitch_variability")
    sr_b = _g(baseline, "speech_rate_wpm")
    sr_c = _g(prosody, "speech_rate_wpm")

    pitch_jump = abs(pv_c - pv_b) / max(1.0, pv_b) if pv_b else 0.0
    rate_jump = abs(sr_c - sr_b) / max(1.0, sr_b) if sr_b else 0.0

    score = _clamp(0.6 * _clamp(pitch_jump / 1.5) + 0.4 * _clamp(rate_jump / 1.0))
    reasons = []
    if pitch_jump > 0.5:
        reasons.append(f"pitch_shift:{pitch_jump:.2f}")
    if rate_jump > 0.5:
        reasons.append(f"speech_rate_shift:{rate_jump:.2f}")

    anomaly = score >= 0.5 and bool(reasons)
    return {
        "anomaly": anomaly,
        "reason": ", ".join(reasons) if reasons else "within_baseline",
        "score": round(score, 3),
    }
