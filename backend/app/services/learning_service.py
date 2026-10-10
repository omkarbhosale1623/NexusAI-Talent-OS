"""Continuous learning from recruiter feedback.

Captures recruiter decisions against AI evaluations, computes agreement /
calibration stats, and derives prompt-bias hints. Pure aggregation — no training.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Evaluation, RecruiterFeedback
from app.services.warehouse_service import stream_event

logger = logging.getLogger(__name__)

# map recruiter decision → comparable recommendation bucket
_DECISION_HIRE = {"hire"}
_DECISION_NO_HIRE = {"no_hire"}
_REC_HIRE = {"strong hire", "hire"}
_REC_NO_HIRE = {"no hire"}


def _rec_bucket(rec: Optional[str]) -> str:
    r = (rec or "").lower()
    if r in _REC_HIRE:
        return "hire"
    if r in _REC_NO_HIRE:
        return "no_hire"
    return "maybe"


def _decision_bucket(decision: str) -> str:
    d = (decision or "").lower()
    if d in _DECISION_HIRE:
        return "hire"
    if d in _DECISION_NO_HIRE:
        return "no_hire"
    return "maybe"


async def record_feedback(
    db: AsyncSession,
    org_id: str,
    interview_id: str,
    recruiter_decision: str,
    recruiter_score: Optional[float] = None,
    rating: Optional[int] = None,
    notes: Optional[str] = None,
    dimension_corrections: Optional[dict] = None,
    user_id: Optional[str] = None,
) -> RecruiterFeedback:
    """Persist recruiter feedback, capturing the AI eval it disagrees/agrees with."""
    stmt = select(Evaluation).where(Evaluation.interview_id == interview_id)
    if org_id:
        stmt = stmt.where(Evaluation.org_id == org_id)
    ev = await db.scalar(stmt)

    ai_rec = ev.recommendation if ev else None
    ai_score = ev.overall_score if ev else None
    agreed = None
    if ai_rec is not None:
        agreed = _rec_bucket(ai_rec) == _decision_bucket(recruiter_decision)

    fb = RecruiterFeedback(
        org_id=org_id,
        interview_id=interview_id,
        evaluation_id=ev.id if ev else None,
        user_id=user_id,
        ai_recommendation=ai_rec,
        ai_score=ai_score,
        recruiter_decision=recruiter_decision,
        recruiter_score=recruiter_score,
        agreed_with_ai=agreed,
        rating=rating,
        notes=notes,
        dimension_corrections=dimension_corrections,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    await stream_event("recruiter_feedback", {
        "id": fb.id, "org_id": org_id, "interview_id": interview_id,
        "ai_recommendation": ai_rec, "ai_score": ai_score,
        "recruiter_decision": recruiter_decision, "agreed_with_ai": agreed,
        "rating": rating,
    })
    return fb


async def _load_feedback(db: AsyncSession, org_id: str) -> List[RecruiterFeedback]:
    stmt = select(RecruiterFeedback)
    if org_id:
        stmt = stmt.where(RecruiterFeedback.org_id == org_id)
    return list((await db.scalars(stmt)).all())


async def learning_stats(db: AsyncSession, org_id: str) -> Dict:
    rows = await _load_feedback(db, org_id)
    count = len(rows)
    if not count:
        return {"count": 0, "agreement_rate": None, "calibration": None,
                "per_recommendation": {}, "avg_rating": None,
                "common_dimension_corrections": {}}

    agreed = [r for r in rows if r.agreed_with_ai is not None]
    agreement_rate = (
        round(sum(1 for r in agreed if r.agreed_with_ai) / len(agreed), 3)
        if agreed else None
    )

    ai_scores = [r.ai_score for r in rows if r.ai_score is not None]
    rec_scores = [r.recruiter_score for r in rows if r.recruiter_score is not None]
    paired = [(r.ai_score, r.recruiter_score) for r in rows
              if r.ai_score is not None and r.recruiter_score is not None]
    calibration = {
        "avg_ai_score": round(sum(ai_scores) / len(ai_scores), 2) if ai_scores else None,
        "avg_recruiter_score": round(sum(rec_scores) / len(rec_scores), 2) if rec_scores else None,
        "avg_score_delta": round(sum(a - r for a, r in paired) / len(paired), 2) if paired else None,
        "paired_n": len(paired),
    }

    per_rec: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "agreed": 0})
    for r in rows:
        if r.ai_recommendation is None or r.agreed_with_ai is None:
            continue
        bucket = per_rec[r.ai_recommendation]
        bucket["total"] += 1
        if r.agreed_with_ai:
            bucket["agreed"] += 1
    per_recommendation = {
        k: {**v, "agreement_rate": round(v["agreed"] / v["total"], 3) if v["total"] else None}
        for k, v in per_rec.items()
    }

    ratings = [r.rating for r in rows if r.rating is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    dim_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"sum": 0.0, "n": 0})
    for r in rows:
        for dim, delta in (r.dimension_corrections or {}).items():
            try:
                d = float(delta)
            except (TypeError, ValueError):
                continue
            dim_totals[dim]["sum"] += d
            dim_totals[dim]["n"] += 1
    common_dimension_corrections = {
        dim: {"avg_correction": round(v["sum"] / v["n"], 2), "count": int(v["n"])}
        for dim, v in dim_totals.items() if v["n"]
    }

    return {
        "count": count,
        "agreement_rate": agreement_rate,
        "calibration": calibration,
        "per_recommendation": per_recommendation,
        "avg_rating": avg_rating,
        "common_dimension_corrections": common_dimension_corrections,
    }


async def calibration_hints(db: AsyncSession, org_id: str) -> Dict:
    """Derive simple bias-adjustment suggestions from aggregated feedback."""
    stats = await learning_stats(db, org_id)
    hints: List[str] = []
    adjustments: Dict[str, float] = {}

    cal = stats.get("calibration") or {}
    delta = cal.get("avg_score_delta")
    if delta is not None and abs(delta) >= 3:
        direction = "over-scores" if delta > 0 else "under-scores"
        hints.append(f"AI {direction} overall by ~{abs(delta):.0f} pts vs recruiters.")
        adjustments["overall"] = -round(delta, 1)

    for dim, info in (stats.get("common_dimension_corrections") or {}).items():
        avg = info["avg_correction"]
        if abs(avg) >= 3:
            direction = "over-scores" if avg < 0 else "under-scores"
            hints.append(f"AI {direction} {dim} by ~{abs(avg):.0f} pts (n={info['count']}).")
            adjustments[dim] = round(avg, 1)

    rate = stats.get("agreement_rate")
    if rate is not None and rate < 0.6:
        hints.append(f"Low AI/recruiter agreement ({rate:.0%}); review prompt rubric.")

    return {
        "count": stats.get("count", 0),
        "agreement_rate": rate,
        "adjustments": adjustments,
        "hints": hints,
    }
