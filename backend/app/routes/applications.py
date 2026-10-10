"""NexusAI Talent OS — Applications Routes"""
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Application, Candidate, Job
from app.schemas.schemas import ApplyRequest, ApplicationResponse, EligibilityResponse, MessageResponse, PaginatedResponse

router = APIRouter()

@router.post("/jobs/{job_id}/apply", response_model=ApplicationResponse, status_code=201)
async def apply_to_job(
    job_id: str,
    full_name: str = Form(...), email: str = Form(...),
    phone: str = Form(default=None), years_experience: float = Form(default=None),
    expected_salary: int = Form(default=None), cover_letter: str = Form(default=None),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.status == "published"))
    if not job: raise HTTPException(404, "Job not found or not accepting applications")
    if resume.size and resume.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Resume too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)")

    # Get or create candidate
    candidate = await db.scalar(select(Candidate).where(Candidate.email == email.lower(), Candidate.org_id == job.org_id))
    if not candidate:
        candidate = Candidate(org_id=job.org_id, full_name=full_name, email=email.lower(), phone=phone)
        db.add(candidate); await db.flush()

    # Check duplicate application
    existing = await db.scalar(select(Application).where(Application.job_id == job_id, Application.candidate_id == candidate.id))
    if existing: raise HTTPException(409, "Already applied to this position")

    # Upload resume to S3
    s3_key = None; resume_filename = resume.filename
    try:
        from app.core.storage import StorageService
        content = await resume.read()
        s3_key = f"resumes/{job.org_id}/{job_id}/{candidate.id}/{resume.filename}"
        storage = StorageService()
        await storage.upload(content, s3_key, resume.content_type or "application/pdf")
    except Exception as e:
        import logging; logging.getLogger(__name__).warning(f"S3 upload failed: {e}")

    app = Application(
        org_id=job.org_id, job_id=job_id, candidate_id=candidate.id,
        status="applied", resume_s3_key=s3_key, resume_filename=resume_filename,
        years_experience=years_experience, expected_salary=expected_salary,
        cover_letter=cover_letter,
    )
    db.add(app); await db.commit(); await db.refresh(app)

    # Trigger async screening
    try:
        from app.services.eligibility_service import screen_application_async
        import asyncio
        asyncio.create_task(screen_application_async(app.id, job.org_id))
    except Exception: pass

    return ApplicationResponse.model_validate(app)

@router.get("", response_model=PaginatedResponse)
async def list_applications(
    request: Request, job_id: Optional[str] = None,
    status: Optional[str] = None, page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.org_id
    q = select(Application).options(selectinload(Application.candidate)).where(Application.org_id == org_id)
    if job_id: q = q.where(Application.job_id == job_id)
    if status: q = q.where(Application.status == status)
    q = q.order_by(Application.applied_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.scalars(q.offset((page-1)*page_size).limit(page_size))).all()
    return PaginatedResponse(
        items=[ApplicationResponse.model_validate(r) for r in rows],
        total=total or 0, page=page, page_size=page_size,
        has_next=(page*page_size) < (total or 0),
    )

@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    app = await db.scalar(
        select(Application).options(selectinload(Application.candidate))
        .where(Application.id == app_id, Application.org_id == request.state.org_id)
    )
    if not app: raise HTTPException(404, "Application not found")
    return ApplicationResponse.model_validate(app)

@router.post("/{app_id}/shortlist", response_model=MessageResponse)
async def shortlist(app_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    app = await db.scalar(select(Application).where(Application.id==app_id, Application.org_id==request.state.org_id))
    if not app: raise HTTPException(404)
    app.status = "shortlisted"; app.shortlisted_at = datetime.utcnow()
    await db.commit()
    # Send shortlist notification async
    try:
        import asyncio
        from app.services.notification_service import send_shortlist_notification
        asyncio.create_task(send_shortlist_notification(app_id))
    except Exception: pass
    return MessageResponse(message="Application shortlisted")

@router.post("/{app_id}/reject", response_model=MessageResponse)
async def reject(app_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    app = await db.scalar(select(Application).where(Application.id==app_id, Application.org_id==request.state.org_id))
    if not app: raise HTTPException(404)
    app.status = "rejected"; app.rejected_at = datetime.utcnow()
    await db.commit()
    return MessageResponse(message="Application rejected")

@router.get("/{app_id}/eligibility", response_model=EligibilityResponse)
async def get_eligibility(app_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    app = await db.scalar(select(Application).where(Application.id==app_id, Application.org_id==request.state.org_id))
    if not app: raise HTTPException(404)
    if not app.eligibility_breakdown:
        raise HTTPException(404, "Eligibility not yet computed — screening in progress")
    bd = app.eligibility_breakdown
    return EligibilityResponse(
        application_id=app_id, overall_score=app.eligibility_score or 0,
        skills_score=bd.get("skills_score", 0), experience_score=bd.get("experience_score", 0),
        education_score=bd.get("education_score", 0), bonus_score=bd.get("bonus_score", 0),
        matched_skills=bd.get("matched_skills", []), missing_skills=bd.get("missing_skills", []),
        recommendation=bd.get("recommendation", "manual_review"),
        reasoning=bd.get("reasoning", ""),
    )
