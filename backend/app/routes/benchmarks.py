"""Benchmark Routes — candidate vs cohort comparison."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.benchmark_service import cohort_benchmark

router = APIRouter()


@router.get("/{interview_id}")
async def get_benchmark(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.FEATURE_BENCHMARKS:
        raise HTTPException(status_code=403, detail="Benchmarks feature disabled")
    org_id = getattr(request.state, "org_id", None)
    result = await cohort_benchmark(db, interview_id, org_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
