"""NexusAI Talent OS — LiveKit WebRTC transport.

Optional dependency: ``livekit-api`` is imported lazily. When it (or the
credentials) are unavailable, every call degrades to ``{ok: False, reason}``.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def livekit_available() -> bool:
    """True only when feature flag + all creds are configured."""
    return bool(
        settings.FEATURE_LIVEKIT
        and settings.LIVEKIT_URL
        and settings.LIVEKIT_API_KEY
        and settings.LIVEKIT_API_SECRET
    )


async def ensure_room(interview_id: str) -> str:
    """Deterministic room name for an interview."""
    return f"nexusai-{interview_id}"


async def create_room_token(
    interview_id: str, identity: str, room: Optional[str] = None
) -> dict:
    """Mint a LiveKit access token with a room_join grant.

    Returns ``{ok, token, url, room}`` on success, else ``{ok: False, reason}``.
    """
    if not livekit_available():
        return {"ok": False, "reason": "livekit_not_configured"}

    room_name = room or await ensure_room(interview_id)

    try:
        from livekit import api  # lazy optional import
    except ImportError:
        return {"ok": False, "reason": "livekit_api_not_installed"}

    try:
        token = (
            api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(identity or f"candidate-{interview_id}")
            .with_name(identity or "candidate")
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
        return {
            "ok": True,
            "token": token,
            "url": settings.LIVEKIT_URL,
            "room": room_name,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"create_room_token failed for {interview_id}: {exc}")
        return {"ok": False, "reason": str(exc)}
