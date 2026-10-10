"""NexusAI Talent OS — Evaluation Routes"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Evaluation
from app.schemas.schemas import EvaluationResponse, EvaluationStatusResponse

router = APIRouter()

@router.post("/{interview_id}", response_model=EvaluationStatusResponse)
async def trigger_evaluation(interview_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    existing = await db.scalar(select(Evaluation).where(Evaluation.interview_id == interview_id))
    if existing:
        return EvaluationStatusResponse(status="completed", evaluation=EvaluationResponse.model_validate(existing))
    try:
        from app.services.evaluation_service import EvaluationService
        svc = EvaluationService(db)
        result = await svc.evaluate_interview(interview_id, org_id)
        return EvaluationStatusResponse(status="completed", evaluation=EvaluationResponse.model_validate(result))
    except Exception as e:
        return EvaluationStatusResponse(status="failed", task_id=str(e))

@router.get("/{interview_id}", response_model=EvaluationStatusResponse)
async def get_evaluation(interview_id: str, db: AsyncSession = Depends(get_db)):
    ev = await db.scalar(
        select(Evaluation).options(selectinload(Evaluation.answer_evaluations))
        .where(Evaluation.interview_id == interview_id)
    )
    if not ev: return EvaluationStatusResponse(status="not_started")
    return EvaluationStatusResponse(status="completed", evaluation=EvaluationResponse.model_validate(ev))
