"""Orchestration routes — multi-agent evaluation pipeline.

Registered under prefix /api/v1/orchestration.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Answer, Candidate, Interview, Job
from app.services.orchestrator_service import graph_available, run_evaluation_pipeline

router = APIRouter()


@router.get("/status")
async def status():
    return {"langgraph": graph_available()}


@router.post("/{interview_id}/run")
async def run_pipeline(interview_id: str, request: Request,
                       db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)

    stmt = select(Interview).where(Interview.id == interview_id)
    if org_id:
        stmt = stmt.where(Interview.org_id == org_id)
    iv = await db.scalar(stmt)
    if iv is None:
        raise HTTPException(status_code=404, detail="interview not found")

    cand = await db.scalar(select(Candidate).where(Candidate.id == iv.candidate_id))
    job = await db.scalar(select(Job).where(Job.id == iv.job_id))

    a_stmt = select(Answer).where(Answer.interview_id == interview_id)
    if org_id:
        a_stmt = a_stmt.where(Answer.org_id == org_id)
    a_stmt = a_stmt.order_by(Answer.created_at)
    answer_rows = list((await db.scalars(a_stmt)).all())

    answers = [{"question_text": a.question_text, "answer_text": a.answer_text,
                "round_type": a.round_type} for a in answer_rows]
    session_data = {
        "interview_id": interview_id,
        "candidate_name": cand.full_name if cand else "N/A",
        "candidate_role": job.title if job else "N/A",
    }

    result = await run_evaluation_pipeline(session_data, answers)
    result["interview_id"] = interview_id
    result["answers_count"] = len(answers)
    return result
