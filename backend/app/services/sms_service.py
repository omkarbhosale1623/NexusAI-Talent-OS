"""NexusAI Talent OS — SMS service (Twilio).

Logs every send as an OutboundMessage. Degrades gracefully when Twilio deps/creds
are missing (status='failed', reason logged). Never raises.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import OutboundMessage

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


# ── Templates ──────────────────────────────────────────────────────────────
def interview_invite_sms(name: str, job: str, url: str) -> str:
    return (
        f"Hi {name}, you're invited to an AI interview for {job}. "
        f"Start here: {url}"
    )


def reminder_sms(name: str, when: str) -> str:
    return f"Hi {name}, reminder: your interview is scheduled for {when}. See you soon!"


# ── Send ───────────────────────────────────────────────────────────────────
async def send_sms(
    db: AsyncSession,
    org_id: str,
    to: str,
    body: str,
    template: Optional[str] = None,
) -> dict:
    msg = OutboundMessage(
        org_id=org_id, channel="sms", to_address=to,
        template=template, body=body, status="queued",
    )
    db.add(msg)
    await db.flush()

    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_FROM_NUMBER
    if not (sid and token and from_number):
        msg.status = "failed"
        msg.error = "twilio_creds_unset"
        await db.flush()
        return {"ok": False, "reason": "twilio_creds_unset", "message_id": msg.id}

    # Prefer SDK; fall back to httpx REST.
    try:
        from twilio.rest import Client  # type: ignore

        try:
            client = Client(sid, token)
            res = client.messages.create(to=to, from_=from_number, body=body)
            msg.provider_id = res.sid
            msg.status = "sent"
            await db.flush()
            return {"ok": True, "provider_id": res.sid, "message_id": msg.id}
        except Exception as e:  # noqa: BLE001
            msg.status = "failed"
            msg.error = f"twilio_send_error:{e}"
            await db.flush()
            return {"ok": False, "reason": msg.error, "message_id": msg.id}
    except ImportError:
        pass  # fall through to httpx

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                TWILIO_API.format(sid=sid),
                data={"To": to, "From": from_number, "Body": body},
                auth=(sid, token),
            )
            r.raise_for_status()
            data = r.json()
        msg.provider_id = data.get("sid")
        msg.status = "sent"
        await db.flush()
        return {"ok": True, "provider_id": data.get("sid"), "message_id": msg.id}
    except Exception as e:  # noqa: BLE001
        msg.status = "failed"
        msg.error = f"twilio_http_error:{e}"
        await db.flush()
        return {"ok": False, "reason": msg.error, "message_id": msg.id}
