"""NexusAI Talent OS — Scheduling Routes"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Interview, InterviewSlot, Job, Candidate, Application
from app.schemas.schemas import BookSlotRequest, MessageResponse, ScheduleInviteResponse, SlotCreate, SlotResponse

router = APIRouter()

@router.post("/slots", response_model=SlotResponse, status_code=201)
async def create_slot(body: SlotCreate, request: Request, db: AsyncSession = Depends(get_db)):
    slot = InterviewSlot(org_id=request.state.org_id, **body.model_dump())
    db.add(slot); await db.commit(); await db.refresh(slot)
    return SlotResponse.model_validate(slot)

@router.get("/slots", response_model=list[SlotResponse])
async def list_slots(
    request: Request, available_only: bool = True,
    job_id: Optional[str] = None, db: AsyncSession = Depends(get_db),
):
    org_id = getattr(request.state, "org_id", None)
    q = select(InterviewSlot).where(InterviewSlot.slot_datetime >= datetime.utcnow())
    if org_id: q = q.where(InterviewSlot.org_id == org_id)
    if available_only: q = q.where(InterviewSlot.is_available == True)
    if job_id: q = q.where(InterviewSlot.job_id == job_id)
    q = q.order_by(InterviewSlot.slot_datetime)
    rows = (await db.scalars(q.limit(50))).all()
    return [SlotResponse.model_validate(r) for r in rows]

@router.get("/by-schedule-token/{token}")
async def get_schedule_info(token: str, db: AsyncSession = Depends(get_db)):
    """Candidate accesses scheduling page via this token."""
    iv = await db.scalar(select(Interview).where(Interview.schedule_token == token))
    if not iv: raise HTTPException(404, "Invalid scheduling link")
    job = await db.get(Job, iv.job_id)
    cand = await db.get(Candidate, iv.candidate_id)
    # Get available slots for this org
    slots = (await db.scalars(
        select(InterviewSlot)
        .where(InterviewSlot.org_id == iv.org_id, InterviewSlot.is_available == True,
               InterviewSlot.slot_datetime >= datetime.utcnow())
        .order_by(InterviewSlot.slot_datetime).limit(20)
    )).all()
    return {
        "interview_id": iv.id,
        "candidate_name": cand.full_name if cand else "",
        "job_title": job.title if job else "",
        "company_name": "",  # from tenant
        "available_slots": [SlotResponse.model_validate(s) for s in slots],
    }

@router.post("/book/{token}", response_model=MessageResponse)
async def book_slot(token: str, body: BookSlotRequest, db: AsyncSession = Depends(get_db)):
    """Candidate books a slot via schedule token."""
    iv = await db.scalar(select(Interview).where(Interview.schedule_token == token))
    if not iv: raise HTTPException(404, "Invalid link")
    slot = await db.get(InterviewSlot, body.slot_id)
    if not slot or not slot.is_available:
        raise HTTPException(400, "Slot not available")
    if slot.current_bookings >= slot.max_bookings:
        raise HTTPException(400, "Slot is full")
    iv.slot_id = slot.id; iv.scheduled_at = slot.slot_datetime; iv.status = "scheduled"
    slot.current_bookings += 1
    if slot.current_bookings >= slot.max_bookings: slot.is_available = False
    await db.commit()
    # Send confirmation + ICS async
    try:
        import asyncio
        from app.services.notification_service import send_interview_confirmation
        asyncio.create_task(send_interview_confirmation(iv.id))
    except Exception: pass
    return MessageResponse(message=f"Interview scheduled for {slot.slot_datetime.strftime('%B %d, %Y at %I:%M %p UTC')}")

@router.post("/send-invite/{interview_id}", response_model=ScheduleInviteResponse)
async def send_schedule_invite(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Admin sends scheduling invite to candidate."""
    iv = await db.scalar(select(Interview).where(Interview.id==interview_id, Interview.org_id==request.state.org_id))
    if not iv: raise HTTPException(404)
    job = await db.get(Job, iv.job_id)
    cand = await db.get(Candidate, iv.candidate_id)
    schedule_link = f"{settings.APP_BASE_URL}/schedule/{iv.schedule_token}"
    expires = datetime.utcnow() + timedelta(hours=settings.MAGIC_LINK_EXPIRE_HOURS)
    iv.invite_sent_at = datetime.utcnow()
    await db.commit()
    try:
        import asyncio
        from app.services.notification_service import send_schedule_invite_email
        asyncio.create_task(send_schedule_invite_email(iv.id, schedule_link))
    except Exception: pass
    return ScheduleInviteResponse(
        schedule_token=iv.schedule_token, schedule_link=schedule_link,
        candidate_name=cand.full_name if cand else "",
        job_title=job.title if job else "", expires_at=expires,
    )
