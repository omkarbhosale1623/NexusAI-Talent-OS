"""NexusAI Talent OS — Calendar sync routes (Google / Outlook)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import CalendarConnection
from app.services import calendar_service as cal

router = APIRouter()


class ConnectionOut(BaseModel):
    id: str
    provider: str
    email: str | None = None
    is_active: bool
    calendar_id: str | None = None


def _guard():
    if not settings.FEATURE_CALENDAR:
        raise HTTPException(403, "Calendar feature disabled")


@router.get("/connections")
async def list_connections(request: Request, db: AsyncSession = Depends(get_db)):
    _guard()
    org_id = getattr(request.state, "org_id", None)
    rows = (await db.scalars(
        select(CalendarConnection).where(CalendarConnection.org_id == org_id)
        .order_by(CalendarConnection.created_at.desc())
    )).all()
    return [ConnectionOut(
        id=r.id, provider=r.provider, email=r.email,
        is_active=r.is_active, calendar_id=r.calendar_id,
    ) for r in rows]


@router.get("/google/connect")
async def google_connect(request: Request):
    _guard()
    org_id = getattr(request.state, "org_id", None) or ""
    if not settings.GOOGLE_CLIENT_ID:
        return {"ok": False, "reason": "google_creds_unset"}
    state = f"{org_id}:{secrets.token_urlsafe(8)}"
    return {"ok": True, "auth_url": cal.google_auth_url(state)}


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    org_id = state.split(":", 1)[0]
    tokens = await cal.google_exchange_code(code)
    if tokens.get("ok"):
        await cal.upsert_connection(db, org_id, "google", tokens, tokens.get("email"))
    return RedirectResponse(f"{settings.APP_BASE_URL}/admin/settings?calendar=google")


@router.get("/outlook/connect")
async def outlook_connect(request: Request):
    _guard()
    org_id = getattr(request.state, "org_id", None) or ""
    if not settings.MS_CLIENT_ID:
        return {"ok": False, "reason": "ms_creds_unset"}
    state = f"{org_id}:{secrets.token_urlsafe(8)}"
    return {"ok": True, "auth_url": cal.outlook_auth_url(state)}


@router.get("/outlook/callback")
async def outlook_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    org_id = state.split(":", 1)[0]
    tokens = await cal.outlook_exchange_code(code)
    if tokens.get("ok"):
        await cal.upsert_connection(db, org_id, "outlook", tokens, tokens.get("email"))
    return RedirectResponse(f"{settings.APP_BASE_URL}/admin/settings?calendar=outlook")


@router.post("/event/{interview_id}")
async def create_event(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _guard()
    return await cal.create_interview_event(db, interview_id)


@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    conn = await db.scalar(
        select(CalendarConnection).where(
            CalendarConnection.id == conn_id, CalendarConnection.org_id == org_id
        )
    )
    if not conn:
        raise HTTPException(404, "Connection not found")
    await db.delete(conn)
    return {"ok": True, "deleted": conn_id}
