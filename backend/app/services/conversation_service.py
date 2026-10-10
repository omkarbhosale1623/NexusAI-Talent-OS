"""
NexusAI Talent OS — Multi-Round Conversation Service
Interview flow: Intro -> Technical -> Behavioral -> HR
Each round has its own question set + follow-up logic.
"""
import asyncio, logging, random
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.database import AsyncSessionLocal
from app.models.models import Answer, Interview, Job, Question, QuestionBank
from app.schemas.schemas import ConversationResponse
from app.services.speech_service import synthesize_speech_b64, precache_next_question_tts
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ROUND_ORDER = ["intro", "technical", "behavioral", "hr"]
ROUND_LABELS = {"intro": "Introduction", "technical": "Technical", "behavioral": "Behavioral", "hr": "HR & Culture Fit"}

_session_locks: dict[str, asyncio.Lock] = {}
_locks_meta_lock = asyncio.Lock()

async def get_session_lock(interview_id: str) -> asyncio.Lock:
    async with _locks_meta_lock:
        if interview_id not in _session_locks:
            _session_locks[interview_id] = asyncio.Lock()
        return _session_locks[interview_id]

ACKS = ["Got it.", "Understood.", "Thank you for that.", "I see.", "Noted.", "All right."]
FOLLOW_UP_INTROS = ["Let me dig a little deeper.", "I'd like to explore that further.", "Could you expand on that?"]
ROUND_TRANSITIONS = {
    "technical":  "Great, that wraps up the introduction. Let's move into some technical questions.",
    "behavioral": "Thanks for sharing that. Now let's talk through some behavioral scenarios.",
    "hr":         "Excellent. For the final part, I have a few questions about culture fit and your goals.",
}

class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService()

    async def handle_conversation_step(
        self, interview_id: str, transcript: Optional[str], current_round: Optional[str] = None,
    ) -> ConversationResponse:
        lock = await get_session_lock(interview_id)
        async with lock:
            return await self._process_step(interview_id, transcript)

    async def _process_step(self, interview_id: str, transcript: Optional[str]) -> ConversationResponse:
        iv = await self.db.scalar(select(Interview).where(Interview.id == interview_id))
        if not iv: raise ValueError(f"Interview {interview_id} not found")

        questions = await self._get_ordered_questions(iv)
        if not questions:
            raise ValueError("No questions available for this interview")

        # ── Greeting ──────────────────────────────────────────────────────
        if transcript is None or iv.status == "scheduled":
            return await self._handle_greeting(iv, questions)

        # ── Already done ─────────────────────────────────────────────────
        if iv.status in ("completed", "evaluated"):
            closing = "This interview has already been completed. Thank you!"
            audio = await synthesize_speech_b64(closing)
            return ConversationResponse(
                bot_text=closing, audio=audio, done=True,
                question_index=iv.current_question_index, total_questions=iv.total_questions,
                current_round=iv.current_round, round_progress=self._round_progress(iv, questions),
            )

        # ── Record answer ────────────────────────────────────────────────
        current_q = questions[iv.current_question_index]
        await self._record_answer(iv, current_q, transcript)

        # ── Quick score for follow-up decision ──────────────────────────
        confidence = await self._quick_score(current_q.text, current_q.expected_answer or "", transcript)
        fu_count = await self._get_follow_up_count(interview_id, current_q.id)

        if settings.FEATURE_FOLLOW_UP and self._needs_follow_up(transcript, confidence, fu_count):
            return await self._handle_follow_up(iv, current_q, transcript, fu_count + 1)

        return await self._advance(iv, questions)

    # ── Question ordering across all 4 rounds ───────────────────────────
    async def _get_ordered_questions(self, iv: Interview) -> list[Question]:
        if not iv.question_bank_id:
            return []
        bank = await self.db.scalar(
            select(QuestionBank).options(selectinload(QuestionBank.questions))
            .where(QuestionBank.id == iv.question_bank_id)
        )
        if not bank: return []
        active = [q for q in bank.questions if q.is_active]

        job = await self.db.get(Job, iv.job_id)
        rounds_config = (job.rounds_config if job else None) or {}

        ordered: list[Question] = []
        for round_name in ROUND_ORDER:
            round_cfg = rounds_config.get(round_name, {"enabled": True, "num_questions": 3})
            if not round_cfg.get("enabled", True): continue
            round_qs = [q for q in active if q.round_type == round_name]
            if not round_qs:  # fallback: take general questions
                round_qs = [q for q in active if not q.round_type][:round_cfg.get("num_questions", 3)]
            random.shuffle(round_qs)
            ordered.extend(round_qs[:round_cfg.get("num_questions", 3)])

        # Persist order if not yet set
        if not iv.question_order:
            iv.question_order = [q.id for q in ordered]
            iv.total_questions = len(ordered)
            await self.db.commit()
        else:
            q_map = {q.id: q for q in ordered}
            ordered = [q_map[qid] for qid in iv.question_order if qid in q_map]
        return ordered

    def _round_progress(self, iv: Interview, questions: list[Question]) -> dict:
        round_counts: dict[str, int] = {}
        for q in questions:
            rt = q.round_type or "general"
            round_counts[rt] = round_counts.get(rt, 0) + 1
        idx_in_round = 0
        seen = 0
        for q in questions[:iv.current_question_index + 1]:
            if q.round_type == iv.current_round: idx_in_round += 1
        return {
            "current_round": iv.current_round,
            "round_label": ROUND_LABELS.get(iv.current_round, iv.current_round),
            "question_in_round": idx_in_round,
            "total_in_round": round_counts.get(iv.current_round, 0),
            "rounds_completed": ROUND_ORDER.index(iv.current_round) if iv.current_round in ROUND_ORDER else 0,
            "total_rounds": len([r for r in ROUND_ORDER if round_counts.get(r)]),
        }

    async def _handle_greeting(self, iv: Interview, questions: list[Question]) -> ConversationResponse:
        iv.status = "active"; iv.started_at = datetime.utcnow()
        iv.current_round = questions[0].round_type or "intro"
        await self.db.commit()

        from app.models.models import Candidate, Job, Tenant
        cand = await self.db.get(Candidate, iv.candidate_id)
        job = await self.db.get(Job, iv.job_id)
        tenant = await self.db.get(Tenant, iv.org_id)

        first_q = questions[0]
        greeting = (
            f"Hello {cand.full_name.split()[0] if cand else 'there'}, welcome to your interview for the "
            f"{job.title if job else 'open'} position at {tenant.name if tenant else 'our company'}. "
            f"This interview has {iv.total_questions} questions across multiple rounds. "
            f"Let's begin with the introduction. {first_q.text}"
        )
        audio = await synthesize_speech_b64(greeting)
        if len(questions) > 1:
            asyncio.create_task(precache_next_question_tts(
                f"{random.choice(ACKS)} {questions[1].text}"
            ))
        return ConversationResponse(
            bot_text=greeting, audio=audio, done=False,
            question_index=0, total_questions=iv.total_questions,
            current_round=iv.current_round, round_progress=self._round_progress(iv, questions),
        )

    async def _record_answer(self, iv: Interview, q: Question, transcript: str):
        wc = len(transcript.split()) if transcript else 0
        ans = Answer(
            interview_id=iv.id, org_id=iv.org_id, question_id=q.id,
            question_text=q.text, answer_text=transcript,
            round_type=iv.current_round, word_count=wc, is_follow_up=False,
        )
        self.db.add(ans); await self.db.commit()
        if settings.FEATURE_ML_PIPELINE:
            try:
                from app.tasks.ml_tasks import analyze_answer_ml_task
                analyze_answer_ml_task.delay(ans.id, iv.org_id)
            except Exception: pass

    async def _quick_score(self, question: str, expected: str, answer: str) -> float:
        if not answer or len(answer.split()) < 5: return 0.2
        try:
            return await self.llm.quick_score(question, expected, answer)
        except Exception:
            return 0.5

    async def _get_follow_up_count(self, interview_id: str, question_id: str) -> int:
        try:
            val = await redis_client.get(f"fu:{interview_id}:{question_id}")
            return int(val) if val else 0
        except Exception:
            return 0

    def _needs_follow_up(self, answer: str, confidence: float, fu_count: int) -> bool:
        if fu_count >= settings.MAX_FOLLOW_UPS_PER_QUESTION: return False
        wc = len(answer.split()) if answer else 0
        if wc < settings.FOLLOW_UP_MIN_WORD_COUNT: return True
        if confidence < settings.FOLLOW_UP_CONFIDENCE_THRESHOLD: return True
        vague = ["i think", "maybe", "not sure", "i guess", "kind of", "i don't know"]
        return any(p in answer.lower() for p in vague)

    async def _handle_follow_up(self, iv: Interview, q: Question, transcript: str, fu_num: int) -> ConversationResponse:
        key = f"fu:{iv.id}:{q.id}"
        await redis_client.incr(key); await redis_client.expire(key, 86400)
        if q.follow_up_hints and fu_num <= len(q.follow_up_hints):
            fu_text = q.follow_up_hints[fu_num - 1]
        else:
            fu_text = await self.llm.generate_follow_up(q.text, transcript, q.expected_answer or "", fu_num)
        bot_text = f"{random.choice(FOLLOW_UP_INTROS)} {fu_text}"
        audio = await synthesize_speech_b64(bot_text)
        questions = await self._get_ordered_questions(iv)
        return ConversationResponse(
            bot_text=bot_text, audio=audio, done=False,
            question_index=iv.current_question_index, total_questions=iv.total_questions,
            current_round=iv.current_round, round_progress=self._round_progress(iv, questions),
            is_follow_up=True, follow_up_number=fu_num,
        )

    async def _advance(self, iv: Interview, questions: list[Question]) -> ConversationResponse:
        next_idx = iv.current_question_index + 1
        if next_idx >= iv.total_questions:
            iv.status = "completed"; iv.completed_at = datetime.utcnow()
            await self.db.commit()
            closing = (
                "That concludes your interview across all rounds. Thank you so much for your time today. "
                "Your responses will be reviewed and you'll hear back soon. Have a great day!"
            )
            audio = await synthesize_speech_b64(closing)
            try:
                from app.services.evaluation_service import evaluate_interview_async
                asyncio.create_task(evaluate_interview_async(iv.id, iv.org_id))
            except Exception: pass
            return ConversationResponse(
                bot_text=closing, audio=audio, done=True,
                question_index=next_idx, total_questions=iv.total_questions,
                current_round=iv.current_round, round_progress=self._round_progress(iv, questions),
            )

        next_q = questions[next_idx]
        round_changed = next_q.round_type != iv.current_round
        new_round = next_q.round_type
        iv.current_question_index = next_idx
        if round_changed: iv.current_round = new_round
        await self.db.commit()

        if round_changed and new_round in ROUND_TRANSITIONS:
            bot_text = f"{ROUND_TRANSITIONS[new_round]} {next_q.text}"
        else:
            bot_text = f"{random.choice(ACKS)} {next_q.text}"

        audio = await synthesize_speech_b64(bot_text)
        if next_idx + 1 < len(questions):
            after = questions[next_idx + 1]
            asyncio.create_task(precache_next_question_tts(f"{random.choice(ACKS)} {after.text}"))

        return ConversationResponse(
            bot_text=bot_text, audio=audio, done=False,
            question_index=next_idx, total_questions=iv.total_questions,
            current_round=iv.current_round, round_progress=self._round_progress(iv, questions),
            round_changed=round_changed, new_round=new_round if round_changed else None,
        )
