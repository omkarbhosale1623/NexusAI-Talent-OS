"""NexusAI Talent OS — LiveKit transport routes.

Mounted under ``/api/v1/livekit``. The token endpoint is candidate-facing: it
looks up the interview by id and, if org context is present, records the chosen
transport/room on the interview.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.models import Interview
from app.services.livekit_service import create_room_token, ensure_room, livekit_available

router = APIRouter()


class TokenIn(BaseModel):
    identity: str = Field(min_length=1, max_length=128)
    interview_token: Optional[str] = Field(default=None, max_length=255)


@router.get("/status")
async def livekit_status():
    return {"available": livekit_available()}


@router.post("/{interview_id}/token")
async def mint_token(
    interview_id: str,
    body: TokenIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Mint a room-join token. A join grant means live access to the interview
    room, so the caller must prove entitlement: either staff auth for the
    interview's org, or the candidate's interview link token."""
    interview = await db.scalar(
        select(Interview).where(Interview.id == interview_id)
    )
    if not interview:
        raise HTTPException(404, "Interview not found")

    org_id = getattr(request.state, "org_id", None)
    is_staff = org_id is not None and org_id == interview.org_id
    is_candidate = (
        body.interview_token is not None
        and secrets.compare_digest(body.interview_token, interview.token or "")
    )
    if not (is_staff or is_candidate):
        raise HTTPException(403, "Interview token or org credentials required")

    if interview.status in ("completed", "evaluated", "cancelled", "no_show"):
        raise HTTPException(409, "Interview is no longer active")

    room = await ensure_room(interview_id)
    result = await create_room_token(interview_id, body.identity, room)
    if not result.get("ok"):
        return result

    interview.transport = "livekit"
    interview.livekit_room = room
    await db.commit()

    return result
