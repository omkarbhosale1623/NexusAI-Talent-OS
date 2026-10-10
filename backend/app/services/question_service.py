"""NexusAI Talent OS — Question Bank Service (upload + AI generation per round)"""
import io, json, logging
from typing import List, Optional
import pandas as pd
from fastapi import UploadFile
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.models import Job, Question, QuestionBank
from app.schemas.schemas import QuestionSchema
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService()

    # ── Parse uploads ─────────────────────────────────────────────────────
    async def parse_upload(self, file: UploadFile) -> List[QuestionSchema]:
        content = await file.read()
        fname = (file.filename or "").lower()
        if fname.endswith(".csv"): return self._parse_csv(content)
        if fname.endswith((".xlsx", ".xls")): return self._parse_excel(content)
        if fname.endswith(".json"): return self._parse_json(content)
        if fname.endswith(".txt"): return self._parse_txt(content)
        if fname.endswith((".docx", ".doc")): return self._parse_docx(content)
        raise ValueError(f"Unsupported file type: {fname}")

    def _parse_csv(self, content: bytes) -> List[QuestionSchema]:
        df = pd.read_csv(io.BytesIO(content))
        return self._df_to_questions(df)

    def _parse_excel(self, content: bytes) -> List[QuestionSchema]:
        df = pd.read_excel(io.BytesIO(content))
        return self._df_to_questions(df)

    def _parse_json(self, content: bytes) -> List[QuestionSchema]:
        data = json.loads(content)
        if isinstance(data, dict):
            for k in ("questions", "items", "bank"):
                if k in data and isinstance(data[k], list):
                    data = data[k]; break
        out = []
        for item in data:
            text = item.get("text") or item.get("question")
            if not text: continue
            out.append(QuestionSchema(
                text=str(text).strip(), topic=item.get("topic"),
                competency=item.get("competency", "general"),
                difficulty=item.get("difficulty", "medium"),
                round_type=item.get("round_type"),
                expected_answer=item.get("expected_answer"),
                keywords=item.get("keywords", []),
                follow_up_hints=item.get("follow_up_hints", []),
            ))
        return out

    def _parse_txt(self, content: bytes) -> List[QuestionSchema]:
        lines = content.decode("utf-8", errors="ignore").splitlines()
        return [QuestionSchema(text=l.strip()) for l in lines if l.strip() and not l.startswith("#")]

    def _parse_docx(self, content: bytes) -> List[QuestionSchema]:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return [QuestionSchema(text=p.text.strip()) for p in doc.paragraphs if len(p.text.strip()) > 10]

    def _df_to_questions(self, df: pd.DataFrame) -> List[QuestionSchema]:
        df.columns = [c.lower().strip() for c in df.columns]
        q_col = next((c for c in ("question", "text", "question_text") if c in df.columns), None)
        if not q_col: raise ValueError(f"No question column found. Columns: {list(df.columns)}")
        out = []
        for _, row in df.iterrows():
            text = str(row.get(q_col, "")).strip()
            if not text or text == "nan": continue
            out.append(QuestionSchema(
                text=text, topic=self._s(row.get("topic")),
                competency=self._s(row.get("competency"), "general"),
                difficulty=self._s(row.get("difficulty"), "medium"),
                round_type=self._s(row.get("round_type")),
                expected_answer=self._s(row.get("expected_answer")),
                keywords=self._lst(row.get("keywords")),
                follow_up_hints=self._lst(row.get("follow_up_hints")),
            ))
        return out

    # ── Save bank ─────────────────────────────────────────────────────────
    async def save_question_bank(
        self, org_id: str, name: str, questions: List[QuestionSchema],
        description: Optional[str] = None, role_tag: Optional[str] = None,
        source: str = "upload",
    ) -> QuestionBank:
        if not questions: raise ValueError("Bank must have at least one question")
        bank = QuestionBank(org_id=org_id, name=name, description=description,
            source=source, role_tag=role_tag, question_count=len(questions))
        self.db.add(bank); await self.db.flush()
        for i, q in enumerate(questions):
            self.db.add(Question(
                bank_id=bank.id, text=q.text, topic=q.topic, competency=q.competency,
                difficulty=q.difficulty, round_type=q.round_type,
                expected_answer=q.expected_answer, keywords=q.keywords,
                follow_up_hints=q.follow_up_hints, order_index=i,
            ))
        await self.db.commit(); await self.db.refresh(bank)
        return bank

    # ── AI generation from Job (NexusAI: multi-round) ──────────────────────
    async def generate_ai_questions_from_job(
        self, org_id: str, job_id: str, application_id: Optional[str] = None,
        num_questions: int = 16, bank_name: Optional[str] = None,
    ) -> QuestionBank:
        job = await self.db.scalar(select(Job).where(Job.id == job_id, Job.org_id == org_id))
        if not job: raise ValueError("Job not found")

        resume_data = {}
        if application_id:
            from app.models.models import Application
            app = await self.db.get(Application, application_id)
            if app and app.parsed_resume:
                resume_data = app.parsed_resume

        rounds_config = job.rounds_config or {
            "intro": {"enabled": True, "num_questions": 3},
            "technical": {"enabled": True, "num_questions": 6},
            "behavioral": {"enabled": True, "num_questions": 4},
            "hr": {"enabled": True, "num_questions": 3},
        }

        all_questions: List[QuestionSchema] = []
        for round_name, cfg in rounds_config.items():
            if not cfg.get("enabled", True): continue
            n = cfg.get("num_questions", 3)
            raw = await self.llm.generate_questions_for_round(
                round_type=round_name, job_title=job.title,
                required_skills=job.required_skills or [],
                resume_data=resume_data, num_questions=n,
            )
            for q in raw:
                text = q.get("text", "").strip()
                if not text: continue
                all_questions.append(QuestionSchema(
                    text=text, competency=q.get("competency", "general"),
                    difficulty=q.get("difficulty", "medium"), round_type=round_name,
                    expected_answer=q.get("expected_answer"),
                    keywords=q.get("keywords", []), follow_up_hints=q.get("follow_up_hints", []),
                ))

        name = bank_name or f"AI Generated — {job.title}"
        bank = await self.save_question_bank(
            org_id=org_id, name=name, questions=all_questions,
            source="ai_generated", role_tag=job.title,
        )
        job.question_bank_id = bank.id
        await self.db.commit()
        return bank

    # ── List / get ────────────────────────────────────────────────────────
    async def get_bank_with_questions(self, bank_id: str, org_id: str) -> Optional[QuestionBank]:
        return await self.db.scalar(
            select(QuestionBank).options(selectinload(QuestionBank.questions))
            .where(QuestionBank.id == bank_id, QuestionBank.org_id == org_id)
        )

    @staticmethod
    def _s(val, default=None):
        if val is None or str(val).strip() in ("nan", "", "None"): return default
        return str(val).strip()

    @staticmethod
    def _lst(val) -> List[str]:
        if val is None: return []
        if isinstance(val, list): return [str(v) for v in val]
        s = str(val).strip()
        if not s or s == "nan": return []
        sep = "|" if "|" in s else ","
        return [v.strip() for v in s.split(sep) if v.strip()]
