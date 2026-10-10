"""Warehouse routes — analytics warehouse status, metrics, backfill.

Registered under prefix /api/v1/warehouse.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Evaluation, Interview
from app.services.warehouse_service import (
    export_evaluation, query_metrics, warehouse_status,
)

router = APIRouter()


@router.get("/status")
async def status():
    return warehouse_status()


@router.get("/metrics")
async def metrics(request: Request, preset: str = "avg_score_by_job"):
    org_id = getattr(request.state, "org_id", None)
    return await query_metrics(org_id, preset)


@router.post("/backfill")
async def backfill(request: Request, limit: int = 100,
                   db: AsyncSession = Depends(get_db)):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(status_code=401, detail="org context required")

    stmt = (
        select(Evaluation, Interview)
        .join(Interview, Interview.id == Evaluation.interview_id)
        .where(Evaluation.org_id == org_id)
        .order_by(Evaluation.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    exported = 0
    failures = 0
    last_reason = None
    for ev, iv in rows:
        row = {
            "interview_id": ev.interview_id,
            "org_id": ev.org_id,
            "job_id": iv.job_id,
            "overall_score": ev.overall_score,
            "recommendation": ev.recommendation,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        res = await export_evaluation(row)
        if res.get("ok"):
            exported += 1
        else:
            failures += 1
            last_reason = res.get("reason")

    return {"candidates": len(rows), "exported": exported,
            "failures": failures, "reason": last_reason}
