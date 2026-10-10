"""NexusAI Talent OS — Bulk resume upload + batch processing.

Reuses ResumeTextExtractor (text extract + LLM parse) and EligibilityService
(scoring) where possible. Every per-file operation is wrapped so a single bad
file never aborts a batch. All writes are org-scoped.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Application, Candidate, Job

logger = logging.getLogger(__name__)


async def _extract_parsed(filename: str, data: bytes) -> dict:
    """Extract text + LLM-parse a resume. Degrade to {} on any failure."""
    try:
        from app.services.resume_parser import ResumeTextExtractor

        return await ResumeTextExtractor().extract_and_parse(data, filename) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Resume parse failed for {filename}: {exc}")
        return {}


def _candidate_fields(parsed: dict, filename: str) -> tuple[str, Optional[str], Optional[str]]:
    full_name = (parsed.get("full_name") or "").strip() or filename.rsplit(".", 1)[0]
    email = (parsed.get("email") or "").strip().lower() or None
    phone = (parsed.get("phone") or "").strip() or None
    return full_name, email, phone


async def process_resume_file(
    db: AsyncSession, org_id: str, job_id: str, filename: str, data: bytes
) -> dict:
    """Process a single resume file end-to-end. Never raises."""
    try:
        job = await db.scalar(
            select(Job).where(Job.id == job_id, Job.org_id == org_id)
        )
        if not job:
            return {"ok": False, "error": "job_not_found", "filename": filename}

        parsed = await _extract_parsed(filename, data)
        full_name, email, phone = _candidate_fields(parsed, filename)

        # Dedupe candidate by (org_id, email); fall back to create.
        candidate: Optional[Candidate] = None
        if email:
            candidate = await db.scalar(
                select(Candidate).where(
                    Candidate.org_id == org_id, Candidate.email == email
                )
            )
        if not candidate:
            candidate = Candidate(
                org_id=org_id, full_name=full_name, email=email or "", phone=phone
            )
            db.add(candidate)
            await db.flush()

        years_exp = parsed.get("years_experience") or None
        app = Application(
            org_id=org_id,
            job_id=job_id,
            candidate_id=candidate.id,
            status="screening",
            resume_filename=filename,
            parsed_resume=parsed or None,
            years_experience=years_exp,
        )
        db.add(app)
        await db.flush()

        score: Optional[float] = None
        status = "screening"
        try:
            from app.services.eligibility_service import EligibilityService

            svc = EligibilityService(db)
            score, breakdown = svc._compute_score(parsed or {}, job, app)
            app.eligibility_score = score
            app.eligibility_breakdown = breakdown
            shortlist = settings.ELIGIBILITY_AUTO_SHORTLIST_THRESHOLD
            reject = settings.ELIGIBILITY_AUTO_REJECT_THRESHOLD
            if score >= shortlist:
                status = "shortlisted"
                app.shortlisted_at = datetime.utcnow()
            elif score < reject:
                status = "rejected"
                app.rejected_at = datetime.utcnow()
            else:
                status = "screening"
            app.status = status
        except Exception as exc:  # noqa: BLE001 — scoring is best-effort
            logger.warning(f"Eligibility scoring failed for {filename}: {exc}")

        await db.commit()
        return {
            "ok": True,
            "candidate_id": candidate.id,
            "application_id": app.id,
            "score": score,
            "status": status,
            "filename": filename,
        }
    except Exception as exc:  # noqa: BLE001 — never let one file kill the batch
        logger.exception(f"process_resume_file failed for {filename}")
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "error": str(exc), "filename": filename}


async def process_batch(
    db: AsyncSession, org_id: str, job_id: str, files: list[tuple[str, bytes]]
) -> dict:
    """Process files sequentially. Enforces BULK_MAX_FILES."""
    max_files = settings.BULK_MAX_FILES
    if len(files) > max_files:
        files = files[:max_files]

    results = []
    for filename, data in files:
        results.append(await process_resume_file(db, org_id, job_id, filename, data))

    succeeded = sum(1 for r in results if r.get("ok"))
    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }
