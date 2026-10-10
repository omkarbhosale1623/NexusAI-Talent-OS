"""NexusAI Talent OS — Jobs Routes"""
from fastapi import APIRouter, Depends, HTTPException, Request, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from typing import Optional
from app.core.database import get_db
from app.models.models import Job, Application
from app.schemas.schemas import JobCreate, JobUpdate, JobResponse, MessageResponse, PaginatedResponse
from datetime import datetime

router = APIRouter()

@router.get("", response_model=PaginatedResponse)
async def list_jobs(
    request: Request,
    status: Optional[str] = None,
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    search: Optional[str] = None,
    org: Optional[str] = None,
    page: int = 1, page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    org_id = getattr(request.state, "org_id", None)
    # Public endpoint: show published jobs only if no auth
    q = select(Job)
    if org_id:
        q = q.where(Job.org_id == org_id)
        if status: q = q.where(Job.status == status)
    else:
        q = q.where(Job.status == "published")
        # White-label embeds link to a single org's board (?org=...);
        # published-only still applies.
        if org: q = q.where(Job.org_id == org)
    if department: q = q.where(Job.department == department)
    if employment_type: q = q.where(Job.employment_type == employment_type)
    if search: q = q.where(Job.title.ilike(f"%{search}%"))
    q = q.order_by(Job.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    jobs = (await db.scalars(q.offset((page-1)*page_size).limit(page_size))).all()
    items = []
    for j in jobs:
        count = await db.scalar(select(func.count()).where(Application.job_id == j.id))
        d = JobResponse.model_validate(j).model_dump()
        d["application_count"] = count or 0
        items.append(d)
    return PaginatedResponse(items=items, total=total or 0, page=page,
        page_size=page_size, has_next=(page*page_size)<(total or 0))

@router.post("", response_model=JobResponse, status_code=201)
async def create_job(body: JobCreate, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    job = Job(org_id=org_id, **body.model_dump())
    db.add(job); await db.commit(); await db.refresh(job)
    return JobResponse.model_validate(job)

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    count = await db.scalar(select(func.count()).where(Application.job_id == job_id))
    d = JobResponse.model_validate(job).model_dump()
    d["application_count"] = count or 0
    return d

@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, body: JobUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(Job).where(Job.id==job_id, Job.org_id==request.state.org_id))
    if not job: raise HTTPException(404, "Job not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(job, k, v)
    await db.commit(); await db.refresh(job)
    return JobResponse.model_validate(job)

@router.post("/{job_id}/publish", response_model=MessageResponse)
async def publish_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(Job).where(Job.id==job_id, Job.org_id==request.state.org_id))
    if not job: raise HTTPException(404, "Job not found")
    job.status = "published"; job.published_at = datetime.utcnow()
    await db.commit()
    return MessageResponse(message="Job published successfully")

@router.post("/{job_id}/archive", response_model=MessageResponse)
async def archive_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(Job).where(Job.id==job_id, Job.org_id==request.state.org_id))
    if not job: raise HTTPException(404, "Job not found")
    job.status = "archived"
    await db.commit()
    return MessageResponse(message="Job archived")

@router.post("/parse-jd", status_code=200)
async def parse_jd(
    request: Request,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    from app.services.resume_parser import ResumeTextExtractor, JDTextParser
    raw_text = ""
    if file:
        content = await file.read()
        extractor = ResumeTextExtractor()
        raw_text = extractor._extract_text(content, file.filename or "job_description.pdf")
    elif text:
        raw_text = text
    else:
        raise HTTPException(status_code=400, detail="Either text or file must be provided")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty")

    parser = JDTextParser()
    parsed_data = await parser.parse(raw_text)
    return parsed_data
