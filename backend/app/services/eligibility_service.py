"""NexusAI Talent OS — Eligibility / Resume Screening Service"""
import asyncio, logging, re
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Application, Candidate, Job

logger = logging.getLogger(__name__)

async def screen_application_async(application_id: str, org_id: str):
    """Fire-and-forget screening after candidate applies."""
    await asyncio.sleep(2)  # Let DB commit settle
    async with AsyncSessionLocal() as db:
        svc = EligibilityService(db)
        await svc.screen(application_id, org_id)

class EligibilityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def screen(self, application_id: str, org_id: str) -> dict:
        app = await self.db.scalar(select(Application).where(Application.id == application_id))
        if not app:
            logger.error(f"Application {application_id} not found")
            return {}
        job = await self.db.get(Job, app.job_id)
        if not job:
            return {}
        # Parse resume if not done
        parsed = app.parsed_resume
        if not parsed and app.resume_s3_key:
            parsed = await self._parse_resume_from_s3(app.resume_s3_key)
            app.parsed_resume = parsed
        # Score
        score, breakdown = self._compute_score(parsed or {}, job, app)
        app.eligibility_score = score
        app.eligibility_breakdown = breakdown
        # Auto-shortlist or auto-reject
        if job.auto_shortlist:
            if score >= settings.ELIGIBILITY_AUTO_SHORTLIST_THRESHOLD:
                app.status = "shortlisted"
                app.shortlisted_at = datetime.utcnow()
                breakdown["recommendation"] = "auto_shortlist"
                logger.info(f"Auto-shortlisted {application_id} (score={score:.2f})")
            elif score < settings.ELIGIBILITY_AUTO_REJECT_THRESHOLD:
                app.status = "rejected"
                app.rejected_at = datetime.utcnow()
                breakdown["recommendation"] = "auto_reject"
                logger.info(f"Auto-rejected {application_id} (score={score:.2f})")
            else:
                app.status = "screening"
                breakdown["recommendation"] = "manual_review"
        else:
            app.status = "screening"
            breakdown["recommendation"] = "manual_review"
        app.eligibility_breakdown = breakdown
        await self.db.commit()
        return breakdown

    def _compute_score(self, parsed: dict, job: Job, app: Application) -> tuple[float, dict]:
        w = settings
        # 1. Skills match (40%)
        required = [s.lower() for s in (job.required_skills or [])]
        candidate_skills = [s.lower() for s in (parsed.get("skills", []) + parsed.get("programming_languages", []) + parsed.get("frameworks", []))]
        matched = [s for s in required if any(s in cs or cs in s for cs in candidate_skills)]
        missing = [s for s in required if s not in [m.lower() for m in matched]]
        skills_score = (len(matched) / len(required)) if required else 0.5

        # 2. Experience match (30%)
        candidate_exp = parsed.get("years_experience", 0) or app.years_experience or 0
        exp_min = job.experience_min or 0
        exp_max = job.experience_max or 99
        if candidate_exp >= exp_min:
            exp_score = min(1.0, candidate_exp / max(exp_min + 1, 1))
        else:
            exp_score = candidate_exp / max(exp_min, 1)
        exp_score = min(1.0, exp_score)

        # 3. Education (20%)
        education = parsed.get("education", [])
        edu_score = 0.5  # neutral default
        degree_weights = {"phd": 1.0, "master": 0.9, "mba": 0.85, "bachelor": 0.75,
                          "associate": 0.5, "diploma": 0.4, "certificate": 0.3}
        for edu in education:
            degree = edu.get("degree", "").lower()
            for kw, w_score in degree_weights.items():
                if kw in degree:
                    edu_score = max(edu_score, w_score)

        # 4. Bonus (10%) — portfolio, LinkedIn
        cand_data = parsed.get("contact", {})
        bonus_score = 0.0
        if cand_data.get("linkedin") or parsed.get("linkedin_url"): bonus_score += 0.5
        if parsed.get("portfolio_url") or parsed.get("github_url"): bonus_score += 0.5

        overall = (
            skills_score * w.ELIGIBILITY_SKILLS_WEIGHT +
            exp_score * w.ELIGIBILITY_EXPERIENCE_WEIGHT +
            edu_score * w.ELIGIBILITY_EDUCATION_WEIGHT +
            bonus_score * w.ELIGIBILITY_BONUS_WEIGHT
        )

        reasoning_parts = []
        if matched: reasoning_parts.append(f"Matched skills: {', '.join(matched[:5])}")
        if missing: reasoning_parts.append(f"Missing skills: {', '.join(missing[:5])}")
        reasoning_parts.append(f"{candidate_exp:.0f} years experience (required: {exp_min}+)")

        return round(overall, 4), {
            "skills_score": round(skills_score, 3),
            "experience_score": round(exp_score, 3),
            "education_score": round(edu_score, 3),
            "bonus_score": round(bonus_score, 3),
            "matched_skills": matched,
            "missing_skills": missing[:10],
            "reasoning": ". ".join(reasoning_parts),
        }

    async def _parse_resume_from_s3(self, s3_key: str) -> dict:
        try:
            from app.core.storage import StorageService
            storage = StorageService()
            content = await storage.download(s3_key)
            filename = s3_key.split("/")[-1]
            from app.services.llm_service import LLMService
            llm = LLMService()
            text = ""
            if filename.endswith(".pdf"):
                import io
                from pdfminer.high_level import extract_text as pdf_text
                text = pdf_text(io.BytesIO(content)) or ""
            elif filename.endswith(".docx"):
                import io
                from docx import Document
                doc = Document(io.BytesIO(content))
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text:
                return await llm.parse_resume(text)
        except Exception as e:
            logger.warning(f"Resume parse from S3 failed: {e}")
        return {}
