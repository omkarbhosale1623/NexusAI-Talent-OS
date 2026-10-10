"""NexusAI Talent OS — Interview Routes (lifecycle + conversation)"""
import asyncio, secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.models import Application, Candidate, Interview, Job
from app.schemas.schemas import ConversationRequest, ConversationResponse, InterviewResponse, MessageResponse, PaginatedResponse

router = APIRouter()

@router.post("", response_model=InterviewResponse, status_code=201)
async def create_interview(
    application_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create an interview session for a shortlisted application."""
    org_id = request.state.org_id
    app = await db.scalar(
        select(Application).options(selectinload(Application.candidate))
        .where(Application.id == application_id, Application.org_id == org_id)
    )
    if not app: raise HTTPException(404, "Application not found")
    if app.status not in ("shortlisted", "interview_scheduled"):
        raise HTTPException(400, "Application must be shortlisted before scheduling interview")

    # Get job for question bank
    job = await db.get(Job, app.job_id)
    interview_token = secrets.token_urlsafe(32)
    schedule_token = secrets.token_urlsafe(24)

    # Calculate question count from rounds config
    rounds_config = (job.rounds_config if job else None) or {
        "intro":      {"enabled": True, "num_questions": 3},
        "technical":  {"enabled": True, "num_questions": 6},
        "behavioral": {"enabled": True, "num_questions": 4},
        "hr":         {"enabled": True, "num_questions": 3},
    }
    total_q = sum(
        r.get("num_questions", 3) for r in rounds_config.values()
        if r.get("enabled", True)
    )

    iv = Interview(
        org_id=org_id, application_id=application_id,
        job_id=app.job_id, candidate_id=app.candidate_id,
        question_bank_id=job.question_bank_id if job else None,
        token=interview_token, schedule_token=schedule_token,
        status="scheduled", total_questions=total_q,
        proctoring_enabled=True,
    )
    db.add(iv)
    app.status = "interview_scheduled"
    await db.commit(); await db.refresh(iv)
    return InterviewResponse.model_validate(iv)

@router.get("", response_model=PaginatedResponse)
async def list_interviews(
    request: Request, status: Optional[str] = None,
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.org_id
    from sqlalchemy import func
    q = select(Interview).where(Interview.org_id == org_id)
    if status: q = q.where(Interview.status == status)
    q = q.order_by(Interview.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.scalars(q.offset((page-1)*page_size).limit(page_size))).all()
    return PaginatedResponse(
        items=[InterviewResponse.model_validate(r) for r in rows],
        total=total or 0, page=page, page_size=page_size,
        has_next=(page*page_size)<(total or 0),
    )

@router.get("/{iv_id}", response_model=InterviewResponse)
async def get_interview(iv_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    q = select(Interview).where(Interview.id == iv_id)
    if org_id: q = q.where(Interview.org_id == org_id)
    iv = await db.scalar(q)
    if not iv: raise HTTPException(404, "Interview not found")
    return InterviewResponse.model_validate(iv)

@router.get("/by-token/{token}", response_model=InterviewResponse)
async def get_by_token(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint — candidate accesses by token."""
    iv = await db.scalar(select(Interview).where(Interview.token == token))
    if not iv: raise HTTPException(404, "Interview not found")
    return InterviewResponse.model_validate(iv)

@router.post("/{iv_id}/start", response_model=MessageResponse)
async def start_interview(iv_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    q = select(Interview).where(Interview.id == iv_id)
    if org_id: q = q.where(Interview.org_id == org_id)
    iv = await db.scalar(q)
    if not iv: raise HTTPException(404)
    iv.status = "active"; iv.started_at = datetime.utcnow()
    # Update application status
    app = await db.get(Application, iv.application_id)
    if app: app.status = "interview_completed"
    await db.commit()
    return MessageResponse(message="Interview started")

@router.post("/{iv_id}/conversation", response_model=ConversationResponse)
async def conversation_step(
    iv_id: str, body: ConversationRequest,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """
    Main speech-to-speech interview loop.
    First call: transcript=None → greeting + Q1 audio.
    Subsequent calls: transcript=<STT text> → evaluate → next question audio.
    Protected by per-session asyncio.Lock.
    """
    from app.services.conversation_service import ConversationService
    svc = ConversationService(db)
    result = await svc.handle_conversation_step(
        interview_id=iv_id,
        transcript=body.transcript,
        current_round=body.current_round,
    )
    return result

@router.post("/{iv_id}/complete", response_model=MessageResponse)
async def complete_interview(iv_id: str, db: AsyncSession = Depends(get_db)):
    iv = await db.get(Interview, iv_id)
    if not iv: raise HTTPException(404)
    iv.status = "completed"; iv.completed_at = datetime.utcnow()
    await db.commit()
    # Trigger evaluation async
    try:
        from app.services.evaluation_service import evaluate_interview_async
        asyncio.create_task(evaluate_interview_async(iv_id, iv.org_id))
    except Exception: pass
    return MessageResponse(message="Interview completed — evaluation in progress")
