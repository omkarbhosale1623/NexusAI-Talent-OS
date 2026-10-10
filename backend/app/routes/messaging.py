"""NexusAI Talent OS — Messaging routes (SMS via Twilio)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Candidate, Interview, Job, OutboundMessage
from app.services import sms_service as sms

router = APIRouter()


class SmsIn(BaseModel):
    to: str
    body: str
    template: str | None = None


class MessageOut(BaseModel):
    id: str
    channel: str
    to_address: str
    template: str | None = None
    status: str
    provider_id: str | None = None
    error: str | None = None


def _guard():
    if not settings.FEATURE_SMS:
        raise HTTPException(403, "SMS feature disabled")


@router.post("/sms")
async def post_sms(payload: SmsIn, request: Request, db: AsyncSession = Depends(get_db)):
    _guard()
    org_id = getattr(request.state, "org_id", None)
    return await sms.send_sms(db, org_id, payload.to, payload.body, payload.template)


@router.get("/messages")
async def list_messages(request: Request, limit: int = 50, db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    rows = (await db.scalars(
        select(OutboundMessage).where(OutboundMessage.org_id == org_id)
        .order_by(OutboundMessage.created_at.desc()).limit(min(limit, 200))
    )).all()
    return [MessageOut(
        id=r.id, channel=r.channel, to_address=r.to_address, template=r.template,
        status=r.status, provider_id=r.provider_id, error=r.error,
    ) for r in rows]


@router.post("/interview/{interview_id}/sms-invite")
async def sms_invite(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _guard()
    org_id = getattr(request.state, "org_id", None)
    iv = await db.scalar(
        select(Interview).where(Interview.id == interview_id, Interview.org_id == org_id)
    )
    if not iv:
        raise HTTPException(404, "Interview not found")
    cand = await db.get(Candidate, iv.candidate_id)
    if not cand or not cand.phone:
        return {"ok": False, "reason": "candidate_phone_missing"}
    job = await db.get(Job, iv.job_id)
    url = f"{settings.APP_BASE_URL}/interview/{iv.token}"
    body = sms.interview_invite_sms(cand.full_name, job.title if job else "a role", url)
    return await sms.send_sms(db, org_id, cand.phone, body, template="interview_invite")
