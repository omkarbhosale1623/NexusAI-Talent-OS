"""gdpr.py — GDPR / data-governance routes (admin/staff only).

Mounted under /api/v1/gdpr (router registered in main.py by the caller).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_admin, require_staff
from app.core.config import settings
from app.core.database import get_db
from app.services.gdpr_service import (
    erase_candidate,
    export_candidate_data,
    purge_expired,
)

router = APIRouter()


class EraseBody(BaseModel):
    hard: bool = False


@router.get("/candidates/{candidate_id}/export", dependencies=[Depends(require_staff)])
async def export_candidate(
    candidate_id: str, request: Request, download: bool = False, db: AsyncSession = Depends(get_db)
):
    """Data-subject access export (DSAR) for one candidate. ?download=1 for a file attachment."""
    try:
        data = await export_candidate_data(db, request.state.org_id, candidate_id)
    except ValueError:
        raise HTTPException(404, "candidate not found")
    if download:
        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": f'attachment; filename="candidate-{candidate_id}-export.json"'
            },
        )
    return data


@router.post("/candidates/{candidate_id}/erase", dependencies=[Depends(require_admin)])
async def erase(
    candidate_id: str, request: Request, body: EraseBody | None = None, db: AsyncSession = Depends(get_db)
):
    """Right-to-erasure. body {hard?: bool}: hard delete vs. anonymize-in-place (default)."""
    try:
        return await erase_candidate(
            db, request.state.org_id, candidate_id, hard=(body.hard if body else False)
        )
    except ValueError:
        raise HTTPException(404, "candidate not found")


@router.post("/retention/run", dependencies=[Depends(require_admin)])
async def run_retention(request: Request):
    """Trigger the retention purge for the caller's org only."""
    return await purge_expired(org_id=request.state.org_id)


@router.get("/policy")
async def policy():
    """Public-ish: configured retention window, data residency, and a short policy summary."""
    days = settings.GDPR_RETENTION_DAYS
    return {
        "retention_days": days,
        "data_residency_region": settings.DATA_RESIDENCY_REGION,
        "summary": (
            f"Candidate personal data is retained for up to {days} days after last activity, "
            "after which personally identifiable information is anonymized. Data subjects may "
            "request a full export (right of access) or erasure (right to be forgotten). "
            f"Data is stored in the '{settings.DATA_RESIDENCY_REGION}' region."
        ),
        "rights": ["access", "erasure", "rectification", "portability"],
    }