"""Learning routes — recruiter feedback + continuous-learning stats.

Registered under prefix /api/v1/learning.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Interview
from app.services.learning_service import (
    calibration_hints, learning_stats, record_feedback,
)

router = APIRouter()


# ── inline schema ────────────────────────────────────────────────────────────
class FeedbackBody(BaseModel):
    interview_id: str
    recruiter_decision: str  # hire|no_hire|maybe
    recruiter_score: Optional[float] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None
    dimension_corrections: Optional[dict] = None


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(status_code=401, detail="org context required")
    return org_id


@router.post("/feedback")
async def submit_feedback(body: FeedbackBody, request: Request,
                          db: AsyncSession = Depends(get_db)):
    if not settings.FEATURE_CONTINUOUS_LEARNING:
        raise HTTPException(status_code=403, detail="Continuous learning disabled")
    org_id = _require_org(request)
    if body.recruiter_decision not in ("hire", "no_hire", "maybe"):
        raise HTTPException(status_code=422, detail="invalid recruiter_decision")
    iv = await db.scalar(select(Interview).where(
        Interview.id == body.interview_id, Interview.org_id == org_id))
    if iv is None:
        raise HTTPException(status_code=404, detail="interview not found")
    user_id = getattr(request.state, "user_id", None)
    fb = await record_feedback(
        db, org_id, body.interview_id, body.recruiter_decision,
        recruiter_score=body.recruiter_score, rating=body.rating,
        notes=body.notes, dimension_corrections=body.dimension_corrections,
        user_id=user_id,
    )
    return {
        "id": fb.id,
        "interview_id": fb.interview_id,
        "evaluation_id": fb.evaluation_id,
        "ai_recommendation": fb.ai_recommendation,
        "ai_score": fb.ai_score,
        "recruiter_decision": fb.recruiter_decision,
        "agreed_with_ai": fb.agreed_with_ai,
    }


@router.get("/stats")
async def stats(request: Request, db: AsyncSession = Depends(get_db)):
    org_id = _require_org(request)
    return await learning_stats(db, org_id)


@router.get("/calibration")
async def calibration(request: Request, db: AsyncSession = Depends(get_db)):
    org_id = _require_org(request)
    return await calibration_hints(db, org_id)
