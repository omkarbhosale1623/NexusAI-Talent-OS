"""NexusAI Talent OS — Question Bank Routes"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Question, QuestionBank
from app.schemas.schemas import QuestionBankResponse, MessageResponse, PaginatedResponse

router = APIRouter()

@router.post("/banks/upload", response_model=QuestionBankResponse, status_code=201)
async def upload_bank(
    request: Request,
    file: UploadFile = File(...),
    bank_name: str = Form(...),
    description: str = Form(default=None),
    role_tag: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")
    from app.services.question_service import QuestionService
    svc = QuestionService(db)
    questions = await svc.parse_upload(file)
    if not questions:
        raise HTTPException(400, "No valid questions found in file")
    bank = await svc.save_question_bank(
        org_id=request.state.org_id, name=bank_name,
        questions=questions, description=description, role_tag=role_tag,
    )
    loaded = await svc.get_bank_with_questions(bank.id, request.state.org_id)
    return QuestionBankResponse.model_validate(loaded)

@router.post("/banks/generate", response_model=QuestionBankResponse, status_code=201)
async def generate_ai_questions(
    request: Request,
    job_id: str = Form(...),
    application_id: str = Form(default=None),
    num_questions: int = Form(default=10),
    bank_name: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not settings.FEATURE_AI_QUESTION_GEN:
        raise HTTPException(501, "AI question generation not enabled")
    from app.services.question_service import QuestionService
    svc = QuestionService(db)
    bank = await svc.generate_ai_questions_from_job(
        org_id=request.state.org_id, job_id=job_id,
        application_id=application_id, num_questions=num_questions,
        bank_name=bank_name,
    )
    loaded = await svc.get_bank_with_questions(bank.id, request.state.org_id)
    return QuestionBankResponse.model_validate(loaded)

@router.get("/banks", response_model=PaginatedResponse)
async def list_banks(request: Request, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    q = select(QuestionBank).where(QuestionBank.org_id == org_id, QuestionBank.is_active == True).order_by(QuestionBank.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    banks = (await db.scalars(q.offset((page-1)*page_size).limit(page_size))).all()
    return PaginatedResponse(items=[QuestionBankResponse.model_validate(b) for b in banks],
        total=total or 0, page=page, page_size=page_size, has_next=(page*page_size)<(total or 0))

@router.get("/banks/{bank_id}", response_model=QuestionBankResponse)
async def get_bank(bank_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from app.services.question_service import QuestionService
    bank = await QuestionService(db).get_bank_with_questions(bank_id, request.state.org_id)
    if not bank: raise HTTPException(404, "Question bank not found")
    return QuestionBankResponse.model_validate(bank)

@router.delete("/banks/{bank_id}", response_model=MessageResponse)
async def delete_bank(bank_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    bank = await db.scalar(select(QuestionBank).where(QuestionBank.id==bank_id, QuestionBank.org_id==request.state.org_id))
    if not bank: raise HTTPException(404)
    bank.is_active = False; await db.commit()
    return MessageResponse(message="Question bank deleted")
