"""NexusAI Talent OS — Bulk resume upload routes.

Mounted under ``/api/v1/bulk``. Org-scoped admin endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.bulk_service import process_batch

router = APIRouter()


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(401, "Organization context required")
    return org_id


@router.post("/upload")
async def upload_resumes(
    request: Request,
    job_id: str = Form(...),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not settings.FEATURE_BULK_UPLOAD:
        raise HTTPException(404, "Bulk upload is disabled")
    org_id = _require_org(request)
    if not files:
        raise HTTPException(400, "No files provided")
    if len(files) > settings.BULK_MAX_FILES:
        raise HTTPException(413, f"Too many files (max {settings.BULK_MAX_FILES})")

    max_bytes = settings.BULK_MAX_FILE_MB * 1024 * 1024
    payload: list[tuple[str, bytes]] = []
    skipped: list[dict] = []
    for f in files:
        name = f.filename or "resume"
        buf = bytearray()
        oversize = False
        while True:
            chunk = await f.read(1024 * 1024)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > max_bytes:
                oversize = True
                break
        if oversize:
            skipped.append({"ok": False, "error": f"file exceeds {settings.BULK_MAX_FILE_MB} MB",
                            "filename": name})
        else:
            payload.append((name, bytes(buf)))

    result = await process_batch(db, org_id, job_id, payload)
    if skipped:
        result["results"] = result.get("results", []) + skipped
        result["failed"] = result.get("failed", 0) + len(skipped)
        result["total"] = result.get("total", 0) + len(skipped)
    return result


@router.get("/status")
async def bulk_status():
    return {
        "max_files": settings.BULK_MAX_FILES,
        "enabled": settings.FEATURE_BULK_UPLOAD,
    }
