"""recording_service.py — Interview video recording lifecycle.

Chunking choice: MVP supports whole-file uploads via `save_recording`.
`append_chunk` buffers each chunk in storage as `{key}.partN`; `finalize_chunks`
downloads the parts in order, concatenates them, uploads the full object under
`{key}`, then deletes the parts. This keeps the happy path (single upload) simple
while still allowing chunked clients to assemble a recording server-side.

All storage calls are wrapped in try/except so a misconfigured/unavailable
S3/R2 backend (common in dev) degrades gracefully instead of 500-ing.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import StorageService
from app.models.models import Interview

logger = logging.getLogger(__name__)


def recording_key(org_id: Optional[str], interview_id: str) -> str:
    """S3/R2 object key for an interview recording."""
    return f"recordings/{org_id or 'public'}/{interview_id}.webm"


def _max_bytes() -> int:
    return int(settings.VIDEO_MAX_SIZE_MB) * 1024 * 1024


async def _get_interview(db: AsyncSession, interview_id: str, org_id: Optional[str]) -> Optional[Interview]:
    stmt = select(Interview).where(Interview.id == interview_id)
    if org_id is not None:
        stmt = stmt.where(Interview.org_id == org_id)
    return await db.scalar(stmt)


async def save_recording(
    db: AsyncSession,
    interview_id: str,
    data: bytes,
    content_type: str,
    duration_s: Optional[float],
) -> dict:
    """Validate, upload, and persist a whole-file interview recording."""
    if not settings.FEATURE_VIDEO_RECORDING:
        return {"ok": False, "reason": "video recording disabled"}

    size = len(data)
    if size == 0:
        return {"ok": False, "reason": "empty upload"}
    if size > _max_bytes():
        return {
            "ok": False,
            "reason": f"recording exceeds VIDEO_MAX_SIZE_MB ({settings.VIDEO_MAX_SIZE_MB} MB)",
            "size_bytes": size,
        }

    iv = await _get_interview(db, interview_id, None)
    if not iv:
        return {"ok": False, "reason": "interview not found"}

    key = recording_key(iv.org_id, interview_id)
    try:
        storage = StorageService()
        await storage.upload(data, key, content_type=content_type or "video/webm")
    except Exception as e:  # noqa: BLE001
        logger.warning("recording upload failed for %s: %s", interview_id, e)
        return {"ok": False, "reason": f"storage unavailable: {e}", "size_bytes": size}

    iv.recording_s3_key = key
    if duration_s is not None:
        iv.recording_duration_seconds = float(duration_s)
    await db.commit()

    return {"ok": True, "key": key, "size_bytes": size, "duration_s": duration_s}


async def append_chunk(
    db: AsyncSession,
    interview_id: str,
    part_number: int,
    data: bytes,
) -> dict:
    """Buffer a single chunk in storage as `{key}.part{N}` (1-indexed)."""
    if not settings.FEATURE_VIDEO_RECORDING:
        return {"ok": False, "reason": "video recording disabled"}

    iv = await _get_interview(db, interview_id, None)
    if not iv:
        return {"ok": False, "reason": "interview not found"}

    base = recording_key(iv.org_id, interview_id)
    part_key = f"{base}.part{part_number}"
    try:
        storage = StorageService()
        await storage.upload(data, part_key, content_type="application/octet-stream")
    except Exception as e:  # noqa: BLE001
        logger.warning("chunk upload failed for %s part %s: %s", interview_id, part_number, e)
        return {"ok": False, "reason": f"storage unavailable: {e}"}

    return {"ok": True, "part_key": part_key, "part_number": part_number, "size_bytes": len(data)}


async def finalize_chunks(
    db: AsyncSession,
    interview_id: str,
    total_parts: int,
    content_type: str = "video/webm",
    duration_s: Optional[float] = None,
) -> dict:
    """Concatenate buffered parts into the final object and persist metadata."""
    if not settings.FEATURE_VIDEO_RECORDING:
        return {"ok": False, "reason": "video recording disabled"}

    iv = await _get_interview(db, interview_id, None)
    if not iv:
        return {"ok": False, "reason": "interview not found"}

    base = recording_key(iv.org_id, interview_id)
    try:
        storage = StorageService()
        buf = bytearray()
        for n in range(1, total_parts + 1):
            buf.extend(await storage.download(f"{base}.part{n}"))
        size = len(buf)
        if size > _max_bytes():
            return {
                "ok": False,
                "reason": f"recording exceeds VIDEO_MAX_SIZE_MB ({settings.VIDEO_MAX_SIZE_MB} MB)",
                "size_bytes": size,
            }
        await storage.upload(bytes(buf), base, content_type=content_type or "video/webm")
        for n in range(1, total_parts + 1):
            try:
                await storage.delete(f"{base}.part{n}")
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("finalize failed for %s: %s", interview_id, e)
        return {"ok": False, "reason": f"storage unavailable: {e}"}

    iv.recording_s3_key = base
    if duration_s is not None:
        iv.recording_duration_seconds = float(duration_s)
    await db.commit()
    return {"ok": True, "key": base, "size_bytes": size, "duration_s": duration_s}


async def playback_url(db: AsyncSession, interview_id: str, org_id: Optional[str]) -> dict:
    """Presigned GET URL for reviewer playback, or a reason if unavailable."""
    iv = await _get_interview(db, interview_id, org_id)
    if not iv:
        return {"url": None, "reason": "interview not found"}
    if not iv.recording_s3_key:
        return {"url": None, "reason": "no recording"}

    expires = int(settings.S3_PRESIGNED_URL_EXPIRY)
    try:
        storage = StorageService()
        url = await storage.presigned_url(iv.recording_s3_key, expires=expires)
    except Exception as e:  # noqa: BLE001
        logger.warning("playback url failed for %s: %s", interview_id, e)
        return {"url": None, "reason": f"storage unavailable: {e}"}

    return {"url": url, "expires_in": expires}


async def delete_recording(db: AsyncSession, interview_id: str, org_id: Optional[str]) -> dict:
    """Delete the stored object and clear recording fields on the interview."""
    iv = await _get_interview(db, interview_id, org_id)
    if not iv:
        return {"ok": False, "reason": "interview not found"}
    key = iv.recording_s3_key
    if key:
        try:
            storage = StorageService()
            await storage.delete(key)
        except Exception as e:  # noqa: BLE001
            logger.warning("recording delete failed for %s: %s", interview_id, e)
            # still clear DB fields so the dangling reference goes away
    iv.recording_s3_key = None
    iv.recording_duration_seconds = None
    await db.commit()
    return {"ok": True, "deleted_key": key}
