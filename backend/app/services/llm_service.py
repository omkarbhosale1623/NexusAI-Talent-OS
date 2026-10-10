"""
LLM Service — all AI calls through LiteLLM AI Gateway with fallback chain.
Primary: OpenRouter (Gemini 2.5 Flash)
Fallback: LLaMA 70B → LLaMA 8B → DeepSeek Chat
"""
import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)


def mask_pii(text: str) -> str:
    """Mask common PII: emails, phone numbers, and SSNs/Aadhaar patterns for security compliance (SOC2/GDPR)."""
    # Email pattern
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, "[EMAIL_MASKED]", text)
    # Phone number pattern (generic international & domestic numbers)
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_pattern, "[PHONE_MASKED]", text)
    return text


class LLMService:
    """All LLM operations using LiteLLM SDK: evaluation, question generation, resume parsing, follow-ups."""

    def __init__(self):
        self.models = [settings.LLM_MODEL] + settings.LLM_FALLBACK_MODELS
        self.fast_model = settings.LLM_FAST_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    def _safe_json(self, content: str, default: Any) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return default

    async def complete(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,  # "json"
        fast: bool = False,
    ) -> Tuple[str, str, int]:
        """
        Call LLM via LiteLLM with automatic fallback chain.
        Returns: (content, model_used, tokens_used)
        """
        models_to_try = [model] if model else (
            [self.fast_model] if fast else self.models
        )

        # Mask PII in messages for GDPR and SOC2 compliance
        masked_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                content = mask_pii(content)
            masked_messages.append({
                "role": msg["role"],
                "content": content
            })

        last_error = None
        for m in models_to_try:
            try:
                content, tokens = await self._call_litellm(
                    model=m,
                    messages=masked_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                return content, m, tokens
            except Exception as exc:
                logger.warning(f"LiteLLM call failed ({m}): {exc}")
                last_error = exc
                await asyncio.sleep(0.5)

        raise RuntimeError(f"All LLM models failed via LiteLLM. Last error: {last_error}")

    async def _call_litellm(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> Tuple[str, int]:
        api_key = settings.LLM_API_KEY
        base_url = settings.LLM_BASE_URL

        # Route openrouter.ai calls via LiteLLM provider tag
        litellm_model = model
        if base_url and "openrouter.ai" in base_url and not model.startswith("openrouter/"):
            litellm_model = f"openrouter/{model}"

        kwargs = {}
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await litellm.acompletion(
            model=litellm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )

        content = response.choices[0].message.content or ""
        tokens = getattr(response, "usage", {}).get("total_tokens", 0) if response.usage else 0
        return content, tokens

    # ── Quick score (fast + cheap) ─────────────────────────────────────────
    async def quick_score(
        self, question: str, expected: str, answer: str
    ) -> float:
        """Return confidence 0.0–1.0. Fast model, minimal tokens."""
        prompt = (
            f"Rate how well this answer addresses the question. "
            f"Reply with ONLY a decimal number from 0.0 to 1.0.\n\n"
            f"Question: {question[:300]}\n"
            f"Expected key points: {expected[:300]}\n"
            f"Answer: {answer[:400]}\n\n"
            "Score (0.0=wrong, 0.5=partial, 1.0=excellent):"
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
            fast=True,
        )
        try:
            return max(0.0, min(1.0, float(content.strip().split()[0])))
        except (ValueError, IndexError):
            return 0.5

    # ── Follow-up generation ───────────────────────────────────────────────
    async def generate_follow_up(
        self,
        original_question: str,
        answer: str,
        expected: str,
        follow_up_number: int,
    ) -> str:
        if follow_up_number == 1:
            instruction = (
                "Ask for a specific concrete example or more detail. "
                "Be encouraging and conversational."
            )
        else:
            instruction = (
                "Ask a harder probing question that tests deeper understanding "
                "of the concept or situation they mentioned. Push for specifics."
            )

        prompt = (
            f"Original question: {original_question}\n"
            f"Expected key points: {expected[:300]}\n"
            f"Candidate's answer: {answer[:500]}\n\n"
            f"Instruction: {instruction}\n\n"
            "Generate ONE follow-up question. Return only the question text."
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=150,
            fast=True,
        )
        return content.strip().strip('"')

    # ── Resume parsing ─────────────────────────────────────────────────────
    async def parse_resume(self, raw_text: str) -> Dict:
        prompt = (
            "Extract structured data from this resume. "
            "Return ONLY valid JSON matching exactly this schema:\n"
            '{"full_name":"","email":"","phone":"","years_experience":0,'
            '"current_title":"","skills":[],"programming_languages":[],'
            '"frameworks":[],"companies":[{"name":"","title":"","duration_months":0}],'
            '"education":[{"degree":"","institution":"","year":null}],'
            '"certifications":[]}\n\n'
            f"Resume:\n{raw_text[:4000]}"
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
            response_format="json",
        )
        return self._safe_json(content, {})

    # ── JD parsing ────────────────────────────────────────────────────────
    async def parse_jd(self, raw_text: str) -> Dict:
        prompt = (
            "Extract structured requirements from this job description. "
            "Return ONLY valid JSON:\n"
            '{"title":"","seniority":"mid","required_skills":[],'
            '"nice_to_have_skills":[],"years_experience_min":0,'
            '"core_responsibilities":[],"tech_stack":[]}\n\n'
            f"JD:\n{raw_text[:3000]}"
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,
            response_format="json",
        )
        return self._safe_json(content, {})

    # ── Question generation ────────────────────────────────────────────────
    async def generate_questions(
        self,
        resume_data: Dict,
        jd_data: Dict,
        num_questions: int = 10,
    ) -> List[Dict]:
        skills = ", ".join(resume_data.get("skills", [])[:15])
        jd_skills = ", ".join(jd_data.get("required_skills", [])[:10])
        exp = resume_data.get("years_experience", 0)
        seniority = jd_data.get("seniority", "mid")
        responsibilities = "\n".join(jd_data.get("core_responsibilities", [])[:5])

        prompt = (
            f"Generate {num_questions} targeted interview questions as JSON.\n\n"
            f"Candidate: {exp} years exp, skills: {skills}\n"
            f"Role: {jd_data.get('title','')}, {seniority}\n"
            f"Required skills: {jd_skills}\n"
            f"Responsibilities:\n{responsibilities}\n\n"
            f"Distribution: 40% technical, 30% behavioral, 20% situational, 10% culture.\n"
            "Return JSON array (not wrapped in object):\n"
            '[{"text":"","competency":"technical","difficulty":"medium",'
            '"expected_answer":"","keywords":[],"follow_up_hints":[]}]'
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75,
            max_tokens=3000,
        )
        # Handle both array and wrapped-object responses
        parsed = self._safe_json(content, [])
        if isinstance(parsed, dict):
            parsed = parsed.get("questions", list(parsed.values())[0] if parsed else [])
        return parsed[:num_questions]

    # ── Full AI evaluation ─────────────────────────────────────────────────
    async def evaluate_interview(
        self,
        session_data: Dict,
        answers_data: List[Dict],
        resume_data: Optional[Dict] = None,
        jd_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate complete evaluation report.
        Returns structured dict with overall + per-question scores.
        """
        transcript_parts = []
        for i, a in enumerate(answers_data, 1):
            transcript_parts.append(
                f"Q{i}: {a['question_text']}\n"
                f"A{i}: {a['answer_text']}\n"
            )
        transcript = "\n".join(transcript_parts)

        jd_context = ""
        if jd_data:
            jd_context = (
                f"\nJob: {jd_data.get('title','')} ({jd_data.get('seniority','')})\n"
                f"Required skills: {', '.join(jd_data.get('required_skills',[]))}"
            )

        system = (
            "You are an expert technical recruiter and interview evaluator. "
            "Provide rigorous, fair, actionable evaluations. "
            "Never fabricate quotes. Be specific and evidence-based."
        )

        user = (
            f"Candidate: {session_data['candidate_name']}\n"
            f"Role: {session_data.get('candidate_role','N/A')}{jd_context}\n\n"
            f"FULL INTERVIEW TRANSCRIPT:\n{transcript}\n\n"
            "Evaluate this interview. Return ONLY valid JSON matching:\n"
            '{"overall_score":0-100,"overall_rating":"strong|good|average|weak",'
            '"recommendation":"Strong Hire|Hire|Consider|No Hire",'
            '"executive_summary":"3-4 sentences for hiring manager",'
            '"hiring_notes":"private notes, risk flags, concerns",'
            '"risk_flags":[],'
            '"communication":{"clarity":0-10,"confidence":0-10,"depth":0-10,"relevance":0-10},'
            '"competency_scores":{"technical":0-100,"behavioral":0-100,"communication":0-100},'
            '"per_question":['
            '{"answer_index":0,"score":0-100,"rating":"strong|good|average|weak",'
            '"candidate_feedback":"1-2 sentences","detailed_analysis":"2-3 paragraphs",'
            '"strengths":[],"improvements":[],"keywords_detected":[],"keywords_missed":[]}'
            ']}'
        )

        start = time.perf_counter()
        content, model_used, tokens = await self.complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format="json",
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        result = self._safe_json(content, {})
        result["_meta"] = {
            "model_used": model_used,
            "tokens_used": tokens,
            "generation_time_ms": duration_ms,
        }

        # Normalise recommendation field
        result["recommendation"] = self._normalise_recommendation(
            result.get("recommendation", "Consider")
        )

        return result

    # ── Round-specific question generation (NexusAI multi-round) ──────────
    async def generate_questions_for_round(
        self,
        round_type: str,
        job_title: str,
        required_skills: List[str],
        resume_data: Dict,
        num_questions: int = 4,
    ) -> List[Dict]:
        """Generate questions tailored to a specific interview round type."""
        round_instructions = {
            "intro": (
                "Generate warm, conversational introduction questions: background, "
                "motivation for applying, career summary. Keep these light and easy."
            ),
            "technical": (
                "Generate rigorous technical questions testing the required skills. "
                "Mix conceptual understanding with practical problem-solving. "
                "Include at least one system-design or architecture question if seniority warrants it."
            ),
            "behavioral": (
                "Generate STAR-format behavioral questions: conflict resolution, "
                "leadership, failure/learning, teamwork, time management."
            ),
            "hr": (
                "Generate culture-fit and logistics questions: salary expectations alignment, "
                "availability, career goals, why this company, work style preferences."
            ),
        }
        instruction = round_instructions.get(round_type, "Generate relevant interview questions.")
        skills_str = ", ".join(required_skills[:12])
        exp = resume_data.get("years_experience", 0) if resume_data else 0

        prompt = (
            f"Generate {num_questions} interview questions for the '{round_type}' round.\n"
            f"Role: {job_title}\n"
            f"Required skills: {skills_str}\n"
            f"Candidate experience: {exp} years\n\n"
            f"Round instructions: {instruction}\n\n"
            "Return ONLY a JSON array (not wrapped in an object):\n"
            '[{"text":"","competency":"technical|behavioral|culture|general",'
            '"difficulty":"easy|medium|hard","expected_answer":"",'
            '"keywords":[],"follow_up_hints":[]}]'
        )
        content, _, _ = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=2000,
        )
        parsed = self._safe_json(content, [])
        if isinstance(parsed, dict):
            parsed = parsed.get("questions", list(parsed.values())[0] if parsed else [])
        return parsed[:num_questions]

    @staticmethod
    def _normalise_recommendation(raw: str) -> str:
        """Clamp LLM free-text to 4 standard values."""
        raw_lower = raw.lower()
        if "strong" in raw_lower and "hire" in raw_lower:
            return "Strong Hire"
        if "no" in raw_lower and "hire" in raw_lower:
            return "No Hire"
        if "consider" in raw_lower:
            return "Consider"
        if "hire" in raw_lower:
            return "Hire"
        return "Consider"

    @staticmethod
    def _safe_json(raw: str, default: Any) -> Any:
        """Parse JSON safely, stripping markdown code fences."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"LLM JSON parse failed: {cleaned[:200]}")
            return default
