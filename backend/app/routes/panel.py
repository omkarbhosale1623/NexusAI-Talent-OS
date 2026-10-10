"""Panel Routes — multi-persona AI interview panel."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_staff
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Answer, Interview, Job
from app.services import panel_service

router = APIRouter()


class QuestionRequest(BaseModel):
    persona_index: int = Field(0, ge=0)
    asked: List[str] = Field(default_factory=list)


def _check_enabled() -> None:
    if not settings.FEATURE_PANEL:
        raise HTTPException(status_code=403, detail="Panel feature disabled")


async def _load_interview(db: AsyncSession, interview_id: str, org_id: Optional[str]) -> Interview:
    q = select(Interview).where(Interview.id == interview_id)
    if org_id:
        q = q.where(Interview.org_id == org_id)
    interview = await db.scalar(q)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


async def _load_job(db: AsyncSession, job_id: str) -> Optional[Job]:
    return await db.scalar(select(Job).where(Job.id == job_id))


@router.get("/{interview_id}/personas")
async def get_personas(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_enabled()
    org_id = getattr(request.state, "org_id", None)
    interview = await _load_interview(db, interview_id, org_id)
    job = await _load_job(db, interview.job_id)
    return {"interview_id": interview_id, "personas": panel_service.resolve_personas(job)}


@router.post("/{interview_id}/question")
async def next_question(
    interview_id: str,
    body: QuestionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _check_enabled()
    org_id = getattr(request.state, "org_id", None)
    interview = await _load_interview(db, interview_id, org_id)
    job = await _load_job(db, interview.job_id)
    personas = panel_service.resolve_personas(job)
    if body.persona_index >= len(personas):
        raise HTTPException(status_code=400, detail="persona_index out of range")
    persona = personas[body.persona_index]

    answers = list((await db.scalars(
        select(Answer).where(Answer.interview_id == interview_id).order_by(Answer.created_at)
    )).all())
    transcript = "\n\n".join(
        f"Q: {a.question_text or ''}\nA: {a.answer_text or ''}" for a in answers
    )
    job_title = job.title if job else "the role"
    question = await panel_service.panel_question(persona, job_title, transcript, body.asked)
    return {
        "interview_id": interview_id,
        "persona": {"name": persona.get("name"), "role": persona.get("role"), "voice": persona.get("voice")},
        "question": question,
    }


@router.post("/{interview_id}/evaluate", dependencies=[Depends(require_staff)])
async def evaluate_panel(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_enabled()
    org_id = getattr(request.state, "org_id", None)
    interview = await _load_interview(db, interview_id, org_id)
    job = await _load_job(db, interview.job_id)
    personas = panel_service.resolve_personas(job)

    answers = list((await db.scalars(
        select(Answer).where(Answer.interview_id == interview_id).order_by(Answer.created_at)
    )).all())
    answer_dicts = [
        {"question_text": a.question_text or "", "answer_text": a.answer_text or ""}
        for a in answers
    ]
    job_title = job.title if job else "the role"
    result = await panel_service.panel_evaluate(personas, answer_dicts, job_title)
    result["interview_id"] = interview_id
    return result
