"""NexusAI Talent OS — ATS integration routes.

Mounted under prefix ``/api/v1/ats``. All endpoints are org-scoped admin
endpoints: ``org_id = request.state.org_id`` is required (401 if missing).
Provider network calls are tolerant and return ``{ok, ...}`` structures.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.models.models import ATSConnection, Application, Candidate, Job, Evaluation, Interview
from app.services.ats import get_provider, SUPPORTED_PROVIDERS

router = APIRouter()


# ── Pydantic (inline) ───────────────────────────────────────────────────────
class ConnectionIn(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None
    config: Optional[dict] = None
    test: bool = Field(default=True, description="Run test_connection on save")


class PushCandidateIn(BaseModel):
    application_id: str


# ── Helpers ──────────────────────────────────────────────────────────────────
def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(401, "Organization context required")
    return org_id


def _check_feature() -> None:
    if not settings.FEATURE_ATS:
        raise HTTPException(404, "ATS integrations are disabled")


def _check_provider(provider: str) -> str:
    p = (provider or "").lower()
    if p not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {provider}")
    return p


def _mask(conn: ATSConnection) -> dict:
    from app.core.crypto import mask_secret
    masked = mask_secret(conn.api_key) or None
    return {
        "id": conn.id,
        "provider": conn.provider,
        "api_key": masked,
        "base_url": conn.base_url,
        "config": conn.config,
        "is_active": conn.is_active,
        "last_sync_at": conn.last_sync_at,
        "last_sync_status": conn.last_sync_status,
        "created_at": conn.created_at,
    }


async def _get_active_connection(db: AsyncSession, org_id: str, provider: str) -> ATSConnection:
    conn = await db.scalar(
        select(ATSConnection).where(
            ATSConnection.org_id == org_id,
            ATSConnection.provider == provider,
            ATSConnection.is_active.is_(True),
        )
    )
    if not conn:
        raise HTTPException(404, f"No active {provider} connection")
    return conn


# ── Connections CRUD ─────────────────────────────────────────────────────────
@router.get("/connections")
async def list_connections(request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    rows = (
        await db.scalars(
            select(ATSConnection)
            .where(ATSConnection.org_id == org_id)
            .order_by(ATSConnection.created_at.desc())
        )
    ).all()
    return {"items": [_mask(r) for r in rows]}


@router.post("/connections")
async def upsert_connection(body: ConnectionIn, request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    provider = _check_provider(body.provider)

    conn = await db.scalar(
        select(ATSConnection).where(
            ATSConnection.org_id == org_id, ATSConnection.provider == provider
        )
    )
    if conn is None:
        conn = ATSConnection(org_id=org_id, provider=provider)
        db.add(conn)
    from app.core.crypto import encrypt
    conn.api_key = encrypt(body.api_key)   # encrypted at rest
    conn.base_url = body.base_url
    conn.config = body.config
    conn.is_active = True

    test_result = None
    if body.test:
        try:
            provider_impl = get_provider(provider, conn)
            test_result = await provider_impl.test_connection()
        except Exception as e:  # never crash on test
            test_result = {"ok": False, "error": str(e)}
        conn.last_sync_status = "connected" if (test_result or {}).get("ok") else "test_failed"

    await db.flush()
    return {"connection": _mask(conn), "test": test_result}


@router.delete("/connections/{connection_id}")
async def deactivate_connection(connection_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    conn = await db.scalar(
        select(ATSConnection).where(
            ATSConnection.id == connection_id, ATSConnection.org_id == org_id
        )
    )
    if not conn:
        raise HTTPException(404, "Connection not found")
    conn.is_active = False
    await db.flush()
    return {"ok": True, "id": conn.id, "is_active": conn.is_active}


# ── Provider operations ──────────────────────────────────────────────────────
@router.post("/{provider}/test")
async def test_provider(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    provider = _check_provider(provider)
    conn = await _get_active_connection(db, org_id, provider)
    try:
        return await get_provider(provider, conn).test_connection()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/{provider}/jobs")
async def provider_jobs(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    provider = _check_provider(provider)
    conn = await _get_active_connection(db, org_id, provider)
    try:
        return await get_provider(provider, conn).list_jobs()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/{provider}/push-candidate")
async def push_candidate(provider: str, body: PushCandidateIn, request: Request, db: AsyncSession = Depends(get_db)):
    _check_feature()
    org_id = _require_org(request)
    provider = _check_provider(provider)
    conn = await _get_active_connection(db, org_id, provider)

    app_row = await db.scalar(
        select(Application).where(
            Application.id == body.application_id, Application.org_id == org_id
        )
    )
    if not app_row:
        raise HTTPException(404, "Application not found")
    cand = await db.scalar(
        select(Candidate).where(
            Candidate.id == app_row.candidate_id, Candidate.org_id == org_id
        )
    )
    if not cand:
        raise HTTPException(404, "Candidate not found")
    job = await db.get(Job, app_row.job_id)

    # Latest evaluation for this application's interview(s), if any.
    evaluation = await db.scalar(
        select(Evaluation)
        .join(Interview, Interview.id == Evaluation.interview_id)
        .where(
            Interview.application_id == app_row.id,
            Evaluation.org_id == org_id,
        )
        .order_by(Evaluation.created_at.desc())
        .limit(1)
    )

    candidate_dict = {
        "full_name": cand.full_name,
        "email": cand.email,
        "phone": cand.phone,
        "job_title": job.title if job else None,
        "eligibility_score": app_row.eligibility_score,
        "application_status": app_row.status,
    }

    impl = get_provider(provider, conn)
    try:
        result = await impl.push_candidate(candidate_dict)
    except Exception as e:
        result = {"ok": False, "error": str(e)}

    eval_result = None
    if result.get("ok") and evaluation is not None:
        candidate_ref = _extract_ref(result.get("data"))
        if candidate_ref:
            eval_payload = {
                "overall_score": evaluation.overall_score,
                "recommendation": evaluation.recommendation,
                "executive_summary": evaluation.executive_summary,
            }
            try:
                eval_result = await impl.push_evaluation(candidate_ref, eval_payload)
            except Exception as e:
                eval_result = {"ok": False, "error": str(e)}

    conn.last_sync_at = datetime.utcnow()
    conn.last_sync_status = "success" if result.get("ok") else "error"
    await db.flush()

    return {"push_candidate": result, "push_evaluation": eval_result}


def _extract_ref(data) -> Optional[str]:
    """Best-effort extraction of a candidate id from a provider response."""
    if not isinstance(data, dict):
        return None
    for key in ("id", "candidate_id"):
        if data.get(key) is not None:
            return str(data[key])
    # Greenhouse nests under "candidate"; Lever under "data".
    for nest in ("candidate", "data"):
        inner = data.get(nest)
        if isinstance(inner, dict) and inner.get("id") is not None:
            return str(inner["id"])
    return None
