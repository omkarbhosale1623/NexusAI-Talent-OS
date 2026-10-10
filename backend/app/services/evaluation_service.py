"""NexusAI Talent OS — 5-Dimension AI Evaluation Service"""
import asyncio, json, logging, time
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.models import Answer, AnswerEvaluation, Candidate, Evaluation, Interview, Job

logger = logging.getLogger(__name__)

ROUND_WEIGHTS = {"intro": 0.10, "technical": 0.45, "behavioral": 0.30, "hr": 0.15}
DIMENSION_WEIGHTS = {"relevance": 0.25, "depth": 0.25, "accuracy": 0.25, "communication": 0.15, "confidence": 0.10}

async def evaluate_interview_async(interview_id: str, org_id: str):
    await asyncio.sleep(1)
    async with AsyncSessionLocal() as db:
        svc = EvaluationService(db)
        try:
            await svc.evaluate_interview(interview_id, org_id)
        except Exception as e:
            logger.error(f"Async evaluation failed {interview_id}: {e}", exc_info=True)

class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_interview(self, interview_id: str, org_id: str) -> Evaluation:
        # Idempotency check
        existing = await self.db.scalar(select(Evaluation).where(Evaluation.interview_id == interview_id))
        if existing:
            logger.info(f"Evaluation already exists for {interview_id}")
            return existing

        iv = await self.db.scalar(
            select(Interview).options(selectinload(Interview.answers))
            .where(Interview.id == interview_id, Interview.org_id == org_id)
        )
        if not iv:
            raise ValueError(f"Interview {interview_id} not found")

        answers = [a for a in iv.answers if not a.is_follow_up]
        if not answers:
            raise ValueError("No answers to evaluate")

        job = await self.db.get(Job, iv.job_id)
        cand = await self.db.get(Candidate, iv.candidate_id)

        # Build evaluation context
        answers_data = [{
            "answer_id": a.id, "question_text": a.question_text,
            "answer_text": a.answer_text, "round_type": a.round_type,
            "word_count": a.word_count,
        } for a in answers]

        from app.services.llm_service import LLMService
        llm = LLMService()
        t0 = time.perf_counter()
        llm_result, model_used, tokens = await llm.complete(
            messages=[
                {"role": "system", "content": (
                    "You are an expert hiring evaluator for NexusAI Talent OS. "
                    "Evaluate each answer across 5 dimensions: Relevance (0-10), "
                    "Depth (0-10), Accuracy (0-10), Communication (0-10), Confidence (0-10). "
                    "Be rigorous, fair, and evidence-based."
                )},
                {"role": "user", "content": self._build_eval_prompt(
                    cand, job, answers_data
                )},
            ],
            temperature=0.3, max_tokens=4000, response_format="json",
        )
        gen_ms = int((time.perf_counter() - t0) * 1000)
        parsed = self._safe_json(llm_result, {})

        # Create Evaluation record
        per_q = parsed.get("per_question", [])
        round_scores = self._aggregate_round_scores(per_q, answers)
        overall = sum(
            round_scores.get(r, 0) * w
            for r, w in ROUND_WEIGHTS.items()
            if round_scores.get(r) is not None
        )
        overall = round(overall, 1)

        competency = parsed.get("competency_scores", {
            "technical": round_scores.get("technical", 0),
            "communication": parsed.get("communication_overall", 7.0),
            "problem_solving": round_scores.get("technical", 0),
            "leadership": round_scores.get("behavioral", 0),
            "culture_fit": round_scores.get("hr", 0),
        })

        salary_rec = None
        if job and job.salary_min and settings_feature_salary():
            salary_rec = self._salary_recommendation(overall, job)

        ev = Evaluation(
            interview_id=interview_id, org_id=org_id,
            overall_score=overall,
            overall_rating=self._rating(overall),
            recommendation=self._normalise_rec(parsed.get("recommendation", "Maybe")),
            executive_summary=parsed.get("executive_summary"),
            hiring_notes=parsed.get("hiring_notes"),
            risk_flags=parsed.get("risk_flags", []),
            communication=parsed.get("communication_dimensions"),
            competency_scores=competency,
            round_scores=round_scores,
            skill_gaps=parsed.get("skill_gaps", []),
            salary_recommendation=salary_rec,
            llm_model_used=model_used,
            llm_tokens_used=tokens,
            generation_time_ms=gen_ms,
        )
        self.db.add(ev); await self.db.flush()

        # Per-answer evaluations
        for i, pq in enumerate(per_q):
            if i >= len(answers): break
            ans = answers[i]
            dims = pq.get("dimensions", {})
            total = sum([
                dims.get("relevance", 5) * DIMENSION_WEIGHTS["relevance"],
                dims.get("depth", 5) * DIMENSION_WEIGHTS["depth"],
                dims.get("accuracy", 5) * DIMENSION_WEIGHTS["accuracy"],
                dims.get("communication", 5) * DIMENSION_WEIGHTS["communication"],
                dims.get("confidence", 5) * DIMENSION_WEIGHTS["confidence"],
            ]) * 10  # scale 0-100
            ae = AnswerEvaluation(
                evaluation_id=ev.id, answer_id=ans.id, org_id=org_id,
                relevance=dims.get("relevance", 5), depth=dims.get("depth", 5),
                accuracy=dims.get("accuracy", 5), communication=dims.get("communication", 5),
                confidence=dims.get("confidence", 5),
                total_score=round(total, 1), rating=self._rating(total),
                candidate_feedback=pq.get("candidate_feedback", ""),
                detailed_analysis=pq.get("detailed_analysis", ""),
                strengths=pq.get("strengths", []),
                improvements=pq.get("improvements", []),
                keywords_detected=pq.get("keywords_detected", []),
            )
            self.db.add(ae)

        from sqlalchemy import update
        await self.db.execute(
            update(Interview).where(Interview.id == interview_id)
            .values(status="evaluated", evaluated_at=datetime.utcnow())
        )
        from app.models.models import Application
        app_rec = await self.db.get(Application, iv.application_id)
        if app_rec:
            app_rec.status = "evaluated"
        await self.db.commit(); await self.db.refresh(ev)

        logger.info(f"Evaluation complete {interview_id}: score={overall}, rec={ev.recommendation}")
        asyncio.create_task(self._send_report_email(ev, iv, cand, job))
        # Emit to the analytics pipeline (Kafka → Spark). No-ops if FEATURE_KAFKA off.
        try:
            from app.services.warehouse_service import stream_event
            asyncio.create_task(stream_event("evaluation_created", {
                "interview_id": interview_id, "org_id": org_id,
                "job_id": iv.job_id, "candidate_id": iv.candidate_id,
                "overall_score": overall, "recommendation": ev.recommendation,
                "created_at": datetime.utcnow().isoformat(),
            }))
        except Exception:
            pass
        return ev

    def _build_eval_prompt(self, cand, job, answers_data: list) -> str:
        transcript = "\n".join(
            f"Q{i+1} [{a['round_type'].upper()}]: {a['question_text']}\n"
            f"A{i+1}: {a['answer_text']}"
            for i, a in enumerate(answers_data)
        )
        return f"""Candidate: {cand.full_name if cand else 'N/A'}
Position: {job.title if job else 'N/A'}
Required Skills: {', '.join(job.required_skills or []) if job else 'N/A'}

INTERVIEW TRANSCRIPT:
{transcript}

Evaluate and return ONLY valid JSON:
{{
  "recommendation": "Strong Hire|Hire|Maybe|No Hire",
  "executive_summary": "3-4 sentences for hiring manager",
  "hiring_notes": "private recruiter notes",
  "risk_flags": [],
  "communication_dimensions": {{"clarity":0-10,"confidence":0-10,"depth":0-10,"relevance":0-10}},
  "competency_scores": {{"technical":0-100,"communication":0-100,"problem_solving":0-100,"leadership":0-100,"culture_fit":0-100}},
  "skill_gaps": [{{"skill":"x","gap":"low|medium|high","recommendation":"..."}}],
  "per_question": [
    {{
      "answer_index": 0,
      "dimensions": {{"relevance":0-10,"depth":0-10,"accuracy":0-10,"communication":0-10,"confidence":0-10}},
      "candidate_feedback": "1-2 sentences",
      "detailed_analysis": "2-3 paragraphs",
      "strengths": [],
      "improvements": [],
      "keywords_detected": []
    }}
  ]
}}"""

    def _aggregate_round_scores(self, per_q: list, answers: list) -> dict:
        round_totals: dict[str, list] = {}
        for i, pq in enumerate(per_q):
            if i >= len(answers): break
            rt = answers[i].round_type
            dims = pq.get("dimensions", {})
            score = sum([
                dims.get("relevance", 5) * DIMENSION_WEIGHTS["relevance"],
                dims.get("depth", 5) * DIMENSION_WEIGHTS["depth"],
                dims.get("accuracy", 5) * DIMENSION_WEIGHTS["accuracy"],
                dims.get("communication", 5) * DIMENSION_WEIGHTS["communication"],
                dims.get("confidence", 5) * DIMENSION_WEIGHTS["confidence"],
            ]) * 10
            round_totals.setdefault(rt, []).append(score)
        return {rt: round(sum(scores)/len(scores), 1) for rt, scores in round_totals.items()}

    def _salary_recommendation(self, score: float, job) -> dict:
        mid = ((job.salary_min or 50000) + (job.salary_max or 100000)) / 2
        pct = 0.95 if score < 60 else (1.0 if score < 75 else (1.05 if score < 88 else 1.10))
        rec_salary = int(mid * pct)
        return {
            "min": int(rec_salary * 0.95), "max": int(rec_salary * 1.05),
            "currency": job.salary_currency, "recommended": rec_salary,
            "justification": f"Based on score {score:.0f}/100 and market benchmarks",
        }

    def _rating(self, score: float) -> str:
        if score >= 85: return "exceptional"
        if score >= 70: return "strong"
        if score >= 55: return "good"
        if score >= 40: return "average"
        return "weak"

    def _normalise_rec(self, raw: str) -> str:
        raw = raw.lower()
        if "strong" in raw and "hire" in raw: return "Strong Hire"
        if "no" in raw and "hire" in raw: return "No Hire"
        if "maybe" in raw or "consider" in raw: return "Maybe"
        if "hire" in raw: return "Hire"
        return "Maybe"

    def _safe_json(self, raw: str, default):
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return default

    async def _send_report_email(self, ev, iv, cand, job):
        try:
            from app.services.notification_service import send_evaluation_report_email
            await send_evaluation_report_email(ev, iv, cand, job)
        except Exception as e:
            logger.warning(f"Report email failed: {e}")

def settings_feature_salary():
    from app.core.config import settings
    return settings.FEATURE_SALARY_RECOMMENDATION
