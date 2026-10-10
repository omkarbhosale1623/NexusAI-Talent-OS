"""NexusAI Talent OS — Interview video recording routes.

Registered under prefix `/api/v1/recordings`.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_admin, require_staff
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Interview
from app.services import recording_service

router = APIRouter()

ALLOWED_RECORDING_TYPES = {
    "video/webm", "video/mp4", "audio/webm", "audio/ogg", "audio/mp4",
}
_CHUNK = 1024 * 1024


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks, aborting as soon as it exceeds max_bytes —
    never buffers an unbounded body in memory."""
    buf = bytearray()
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            return bytes(buf)
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise HTTPException(
                413, f"Recording exceeds VIDEO_MAX_SIZE_MB ({settings.VIDEO_MAX_SIZE_MB} MB)")


# ── inline schemas ─────────────────────────────────────────────────────────
class UploadResult(BaseModel):
    ok: bool
    key: Optional[str] = None
    size_bytes: Optional[int] = None
    duration_s: Optional[float] = None
    reason: Optional[str] = None


class PlaybackResult(BaseModel):
    url: Optional[str] = None
    expires_in: Optional[int] = None
    reason: Optional[str] = None


class MetaResult(BaseModel):
    has_recording: bool
    duration_s: Optional[float] = None
    key_present: bool


class DeleteResult(BaseModel):
    ok: bool
    deleted_key: Optional[str] = None
    reason: Optional[str] = None


# ── routes ─────────────────────────────────────────────────────────────────
@router.post("/{interview_id}/upload", response_model=UploadResult)
async def upload_recording(
    interview_id: str,
    request: Request,
    file: UploadFile = File(...),
    duration_s: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Candidate-facing whole-file recording upload (org_id may be None)."""
    if not settings.FEATURE_VIDEO_RECORDING:
        raise HTTPException(403, "Video recording is disabled")

    content_type = (file.content_type or "video/webm").split(";")[0].strip().lower()
    if content_type not in ALLOWED_RECORDING_TYPES:
        raise HTTPException(415, f"Unsupported recording content type: {content_type}")

    # One recording per interview — re-uploads can't silently replace evidence.
    existing = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if not existing:
        raise HTTPException(404, "Interview not found")
    if existing.recording_s3_key:
        raise HTTPException(409, "A recording already exists for this interview")

    data = await _read_capped(file, settings.VIDEO_MAX_SIZE_MB * 1024 * 1024)

    result = await recording_service.save_recording(
        db, interview_id, data,
        content_type=content_type,
        duration_s=duration_s,
    )
    if not result.get("ok") and result.get("reason") == "interview not found":
        raise HTTPException(404, "Interview not found")
    return UploadResult(**result)


@router.get("/{interview_id}/playback", response_model=PlaybackResult,
            dependencies=[Depends(require_staff)])
async def get_playback(
    interview_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin/reviewer (org-scoped) presigned playback URL."""
    org_id = getattr(request.state, "org_id", None)
    result = await recording_service.playback_url(db, interview_id, org_id)
    if result.get("reason") == "interview not found":
        raise HTTPException(404, "Interview not found")
    return PlaybackResult(**result)


@router.get("/{interview_id}/meta", response_model=MetaResult)
async def get_meta(
    interview_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Lightweight recording metadata for an interview."""
    org_id = getattr(request.state, "org_id", None)
    stmt = select(Interview).where(Interview.id == interview_id)
    if org_id is not None:
        stmt = stmt.where(Interview.org_id == org_id)
    iv = await db.scalar(stmt)
    if not iv:
        raise HTTPException(404, "Interview not found")
    key_present = bool(iv.recording_s3_key)
    return MetaResult(
        has_recording=key_present,
        duration_s=iv.recording_duration_seconds,
        key_present=key_present,
    )


@router.delete("/{interview_id}", response_model=DeleteResult,
               dependencies=[Depends(require_admin)])
async def delete_recording(
    interview_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin (org-scoped): delete recording object and clear fields."""
    org_id = getattr(request.state, "org_id", None)
    result = await recording_service.delete_recording(db, interview_id, org_id)
    if not result.get("ok") and result.get("reason") == "interview not found":
        raise HTTPException(404, "Interview not found")
    return DeleteResult(**result)
