"""NexusAI Talent OS — Candidates Routes"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Candidate, Application, Interview
from app.schemas.schemas import CandidateResponse, PaginatedResponse, PortalAccessResponse

router = APIRouter()

@router.get("", response_model=PaginatedResponse)
async def list_candidates(request: Request, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    q = select(Candidate).where(Candidate.org_id == org_id).order_by(Candidate.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.scalars(q.offset((page-1)*page_size).limit(page_size))).all()
    return PaginatedResponse(items=[CandidateResponse.model_validate(r) for r in rows],
        total=total or 0, page=page, page_size=page_size, has_next=(page*page_size)<(total or 0))

@router.get("/portal/{token}", response_model=PortalAccessResponse)
async def candidate_portal(token: str, db: AsyncSession = Depends(get_db)):
    """Candidate accesses their portal via interview token."""
    iv = await db.scalar(
        select(Interview).options(selectinload(Interview.application))
        .where(Interview.token == token)
    )
    if not iv: raise HTTPException(404, "Invalid token")
    cand = await db.get(Candidate, iv.candidate_id)
    from app.models.models import Job, Tenant, Evaluation
    job = await db.get(Job, iv.job_id)
    tenant = await db.get(Tenant, iv.org_id)
    ev = await db.scalar(select(Evaluation).where(Evaluation.interview_id == iv.id))
    from app.core.config import settings
    return PortalAccessResponse(
        candidate_name=cand.full_name if cand else "",
        job_title=job.title if job else "",
        company_name=tenant.name if tenant else "NexusAI",
        application_status=iv.application.status if iv.application else "unknown",
        interview_status=iv.status,
        interview_scheduled_at=iv.scheduled_at,
        can_schedule=iv.status == "scheduled" and not iv.scheduled_at,
        can_join_interview=iv.status in ("scheduled", "ready"),
        can_view_report=ev is not None and settings.FEATURE_CANDIDATE_REPORT_VIEW,
        report_shared=ev.candidate_report_shared if ev else False,
    )

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    c = await db.scalar(select(Candidate).where(Candidate.id==candidate_id, Candidate.org_id==request.state.org_id))
    if not c: raise HTTPException(404)
    return CandidateResponse.model_validate(c)
