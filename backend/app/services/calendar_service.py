"""NexusAI Talent OS — Calendar sync service (Google Calendar + Microsoft Graph).

Degrades gracefully: if SDK/deps missing or creds unset, returns {ok: False, reason}.
Uses httpx for OAuth token exchange + REST calls (simpler than full SDKs here).
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import CalendarConnection, Interview, Candidate, Job, Tenant

# ── Constants ──────────────────────────────────────────────────────────────
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events openid email"

MS_AUTH = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MS_TOKEN = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
MS_EVENTS = "https://graph.microsoft.com/v1.0/me/events"
MS_SCOPES = "offline_access openid email Calendars.ReadWrite"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Google ─────────────────────────────────────────────────────────────────
def google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH}?{urllib.parse.urlencode(params)}"


async def google_exchange_code(code: str) -> dict:
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        return {"ok": False, "reason": "google_creds_unset"}
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(GOOGLE_TOKEN, data=data)
            r.raise_for_status()
            tok = r.json()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"google_token_error:{e}"}
    return {
        "ok": True,
        "access_token": tok.get("access_token"),
        "refresh_token": tok.get("refresh_token"),
        "expires_in": tok.get("expires_in"),
        "email": _google_email(tok.get("id_token")),
    }


def _google_email(id_token: Optional[str]) -> Optional[str]:
    if not id_token:
        return None
    try:
        import base64
        import json
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("email")
    except Exception:  # noqa: BLE001
        return None


async def _google_refresh(conn: CalendarConnection) -> Optional[str]:
    from app.core.crypto import decrypt, encrypt
    if not conn.refresh_token or not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        return None
    data = {
        "refresh_token": decrypt(conn.refresh_token),
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(GOOGLE_TOKEN, data=data)
            r.raise_for_status()
            tok = r.json()
    except Exception:  # noqa: BLE001
        return None
    at = tok.get("access_token")
    conn.access_token = encrypt(at)
    if tok.get("expires_in"):
        conn.token_expires_at = _now() + timedelta(seconds=int(tok["expires_in"]))
    return at


async def google_create_event(
    conn: CalendarConnection,
    summary: str,
    start_iso: str,
    end_iso: str,
    attendees: Optional[list[str]] = None,
    description: str = "",
) -> dict:
    from app.core.crypto import decrypt
    token = decrypt(conn.access_token)
    if conn.token_expires_at and conn.token_expires_at <= _now():
        token = await _google_refresh(conn) or token
    if not token:
        return {"ok": False, "reason": "no_access_token"}
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
        "attendees": [{"email": a} for a in (attendees or []) if a],
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                GOOGLE_EVENTS,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                params={"sendUpdates": "all"},
            )
            if r.status_code == 401:
                token = await _google_refresh(conn)
                if not token:
                    return {"ok": False, "reason": "unauthorized"}
                r = await c.post(
                    GOOGLE_EVENTS, json=body,
                    headers={"Authorization": f"Bearer {token}"},
                    params={"sendUpdates": "all"},
                )
            r.raise_for_status()
            ev = r.json()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"google_event_error:{e}"}
    return {"ok": True, "event_id": ev.get("id"), "html_link": ev.get("htmlLink")}


# ── Outlook / Microsoft Graph ──────────────────────────────────────────────
def outlook_auth_url(state: str) -> str:
    params = {
        "client_id": settings.MS_CLIENT_ID,
        "redirect_uri": settings.MS_REDIRECT_URI,
        "response_type": "code",
        "response_mode": "query",
        "scope": MS_SCOPES,
        "state": state,
    }
    base = MS_AUTH.format(tenant=settings.MS_TENANT_ID or "common")
    return f"{base}?{urllib.parse.urlencode(params)}"


async def outlook_exchange_code(code: str) -> dict:
    if not (settings.MS_CLIENT_ID and settings.MS_CLIENT_SECRET):
        return {"ok": False, "reason": "ms_creds_unset"}
    data = {
        "code": code,
        "client_id": settings.MS_CLIENT_ID,
        "client_secret": settings.MS_CLIENT_SECRET,
        "redirect_uri": settings.MS_REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": MS_SCOPES,
    }
    url = MS_TOKEN.format(tenant=settings.MS_TENANT_ID or "common")
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(url, data=data)
            r.raise_for_status()
            tok = r.json()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"ms_token_error:{e}"}
    return {
        "ok": True,
        "access_token": tok.get("access_token"),
        "refresh_token": tok.get("refresh_token"),
        "expires_in": tok.get("expires_in"),
        "email": None,
    }


async def _outlook_refresh(conn: CalendarConnection) -> Optional[str]:
    from app.core.crypto import decrypt, encrypt
    if not conn.refresh_token or not (settings.MS_CLIENT_ID and settings.MS_CLIENT_SECRET):
        return None
    data = {
        "refresh_token": decrypt(conn.refresh_token),
        "client_id": settings.MS_CLIENT_ID,
        "client_secret": settings.MS_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "scope": MS_SCOPES,
    }
    url = MS_TOKEN.format(tenant=settings.MS_TENANT_ID or "common")
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(url, data=data)
            r.raise_for_status()
            tok = r.json()
    except Exception:  # noqa: BLE001
        return None
    at = tok.get("access_token")
    conn.access_token = encrypt(at)
    if tok.get("refresh_token"):
        conn.refresh_token = encrypt(tok["refresh_token"])
    if tok.get("expires_in"):
        conn.token_expires_at = _now() + timedelta(seconds=int(tok["expires_in"]))
    return at


async def outlook_create_event(
    conn: CalendarConnection,
    summary: str,
    start_iso: str,
    end_iso: str,
    attendees: Optional[list[str]] = None,
    description: str = "",
) -> dict:
    from app.core.crypto import decrypt
    token = decrypt(conn.access_token)
    if conn.token_expires_at and conn.token_expires_at <= _now():
        token = await _outlook_refresh(conn) or token
    if not token:
        return {"ok": False, "reason": "no_access_token"}
    body = {
        "subject": summary,
        "body": {"contentType": "HTML", "content": description},
        "start": {"dateTime": start_iso, "timeZone": "UTC"},
        "end": {"dateTime": end_iso, "timeZone": "UTC"},
        "attendees": [
            {"emailAddress": {"address": a}, "type": "required"}
            for a in (attendees or []) if a
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                MS_EVENTS, json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 401:
                token = await _outlook_refresh(conn)
                if not token:
                    return {"ok": False, "reason": "unauthorized"}
                r = await c.post(
                    MS_EVENTS, json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
            r.raise_for_status()
            ev = r.json()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"ms_event_error:{e}"}
    return {"ok": True, "event_id": ev.get("id"), "html_link": ev.get("webLink")}


# ── Persistence + orchestration ────────────────────────────────────────────
async def upsert_connection(
    db: AsyncSession,
    org_id: str,
    provider: str,
    tokens: dict,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
) -> CalendarConnection:
    conn = await db.scalar(
        select(CalendarConnection).where(
            CalendarConnection.org_id == org_id,
            CalendarConnection.provider == provider,
        )
    )
    expires_at = None
    if tokens.get("expires_in"):
        expires_at = _now() + timedelta(seconds=int(tokens["expires_in"]))
    if conn is None:
        conn = CalendarConnection(org_id=org_id, provider=provider, user_id=user_id)
        db.add(conn)
    from app.core.crypto import encrypt
    if tokens.get("access_token"):
        conn.access_token = encrypt(tokens["access_token"])   # encrypted at rest
    if tokens.get("refresh_token"):
        conn.refresh_token = encrypt(tokens["refresh_token"])
    conn.token_expires_at = expires_at or conn.token_expires_at
    conn.email = email or tokens.get("email") or conn.email
    conn.is_active = True
    await db.flush()
    return conn


async def create_interview_event(db: AsyncSession, interview_id: str) -> dict:
    iv = await db.get(Interview, interview_id)
    if not iv:
        return {"ok": False, "reason": "interview_not_found"}
    if not iv.scheduled_at:
        return {"ok": False, "reason": "not_scheduled"}
    conn = await db.scalar(
        select(CalendarConnection).where(
            CalendarConnection.org_id == iv.org_id,
            CalendarConnection.is_active.is_(True),
        ).order_by(CalendarConnection.created_at.desc())
    )
    if not conn:
        return {"ok": False, "reason": "no_active_connection"}

    cand = await db.get(Candidate, iv.candidate_id)
    job = await db.get(Job, iv.job_id)
    tenant = await db.get(Tenant, iv.org_id)
    company = tenant.name if tenant else "NexusAI"
    title = job.title if job else "Interview"
    cand_name = cand.full_name if cand else "Candidate"

    start = iv.scheduled_at
    end = start + timedelta(minutes=getattr(settings, "SCHEDULE_WINDOW_MINUTES", 60) or 60)
    start_iso = start.replace(microsecond=0).isoformat()
    end_iso = end.replace(microsecond=0).isoformat()
    summary = f"Interview: {cand_name} — {title} @ {company}"
    join_url = f"{settings.APP_BASE_URL}/interview/{iv.token}"
    description = f"AI interview for {title}.\nJoin: {join_url}"
    attendees = [cand.email] if cand and cand.email else []

    if conn.provider == "google":
        res = await google_create_event(conn, summary, start_iso, end_iso, attendees, description)
    elif conn.provider == "outlook":
        res = await outlook_create_event(conn, summary, start_iso, end_iso, attendees, description)
    else:
        return {"ok": False, "reason": f"unknown_provider:{conn.provider}"}
    await db.flush()
    res["provider"] = conn.provider
    return res
