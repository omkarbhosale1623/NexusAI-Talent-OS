"""gdpr_service.py — GDPR / data-governance: data-subject export, right-to-erasure, retention purge.

Org-scoped where a caller's org is known; the platform-wide retention job is org-agnostic.
All ops are defensive: storage failures and per-row errors are collected, never crash the whole op.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage import StorageService
from app.models.models import (
    Answer,
    AnswerEvaluation,
    Application,
    AuditLog,
    Candidate,
    CodingSubmission,
    Evaluation,
    Interview,
    OutboundMessage,
    ProctoringEvent,
    RecruiterFeedback,
)

logger = logging.getLogger(__name__)

ANON_NAME = "REDACTED"


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else v


def _row(obj: Any) -> dict:
    """Serialize a SQLAlchemy model row to a JSON-safe dict (datetimes -> iso)."""
    return {c.key: _iso(getattr(obj, c.key)) for c in obj.__table__.columns}


async def export_candidate_data(db: AsyncSession, org_id: str, candidate_id: str) -> dict:
    """Assemble a full data-subject-access (DSAR) export for one candidate. Org-scoped."""
    cand = await db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.org_id == org_id)
    )
    if not cand:
        raise ValueError("candidate not found")

    apps = (await db.scalars(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.org_id == org_id
        )
    )).all()

    interviews = (await db.scalars(
        select(Interview).where(
            Interview.candidate_id == candidate_id, Interview.org_id == org_id
        )
    )).all()
    interview_ids = [iv.id for iv in interviews]

    answers = evaluations = answer_evals = coding = proctoring = []
    if interview_ids:
        answers = (await db.scalars(
            select(Answer).where(Answer.interview_id.in_(interview_ids))
        )).all()
        evaluations = (await db.scalars(
            select(Evaluation).where(Evaluation.interview_id.in_(interview_ids))
        )).all()
        eval_ids = [e.id for e in evaluations]
        if eval_ids:
            answer_evals = (await db.scalars(
                select(AnswerEvaluation).where(AnswerEvaluation.evaluation_id.in_(eval_ids))
            )).all()
        coding = (await db.scalars(
            select(CodingSubmission).where(CodingSubmission.interview_id.in_(interview_ids))
        )).all()
        proctoring = (await db.scalars(
            select(ProctoringEvent).where(ProctoringEvent.interview_id.in_(interview_ids))
        )).all()

    feedback = (await db.scalars(
        select(RecruiterFeedback).where(
            RecruiterFeedback.interview_id.in_(interview_ids), RecruiterFeedback.org_id == org_id
        )
    )).all() if interview_ids else []

    # Outbound messages addressed to the candidate's contact details.
    addrs = [a for a in (cand.email, cand.phone) if a]
    messages = (await db.scalars(
        select(OutboundMessage).where(
            OutboundMessage.org_id == org_id, OutboundMessage.to_address.in_(addrs)
        )
    )).all() if addrs else []

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "org_id": org_id,
        "candidate": _row(cand),
        "applications": [_row(a) for a in apps],
        "interviews": [_row(iv) for iv in interviews],
        "answers": [_row(a) for a in answers],
        "evaluations": [_row(e) for e in evaluations],
        "answer_evaluations": [_row(ae) for ae in answer_evals],
        "coding_submissions": [_row(cs) for cs in coding],
        "proctoring_events": [_row(p) for p in proctoring],
        "recruiter_feedback": [_row(f) for f in feedback],
        "outbound_messages": [_row(m) for m in messages],
    }


def _is_anonymized(cand: Candidate) -> bool:
    return cand.full_name == ANON_NAME or cand.email.startswith("redacted+")


async def erase_candidate(
    db: AsyncSession, org_id: str, candidate_id: str, hard: bool = False
) -> dict:
    """Right-to-erasure. hard=True deletes rows (FK-safe order); hard=False anonymizes PII in place.

    Always best-effort: storage delete failures and per-row errors are collected, not raised.
    Writes an AuditLog row (action="gdpr_erase").
    """
    errors: list[str] = []
    storage_deleted = 0
    storage = StorageService()

    cand = await db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.org_id == org_id)
    )
    if not cand:
        raise ValueError("candidate not found")

    apps = (await db.scalars(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.org_id == org_id
        )
    )).all()
    interviews = (await db.scalars(
        select(Interview).where(
            Interview.candidate_id == candidate_id, Interview.org_id == org_id
        )
    )).all()
    interview_ids = [iv.id for iv in interviews]
    answers = (await db.scalars(
        select(Answer).where(Answer.interview_id.in_(interview_ids))
    )).all() if interview_ids else []

    # ── Best-effort storage object deletion ────────────────────────────────
    keys: list[str] = []
    keys += [a.resume_s3_key for a in apps if a.resume_s3_key]
    keys += [iv.recording_s3_key for iv in interviews if iv.recording_s3_key]
    keys += [a.audio_s3_key for a in answers if a.audio_s3_key]
    for key in keys:
        try:
            await storage.delete(key)
            storage_deleted += 1
        except Exception as e:  # noqa: BLE001 — never fail erase on storage error
            errors.append(f"storage:{key}:{e}")

    result: dict[str, Any] = {"ok": True, "storage_deleted": storage_deleted}

    if hard:
        # ── Hard delete: children first, parents last (FK-safe) ────────────
        deleted: dict[str, int] = {}
        eval_ids = []
        if interview_ids:
            evals = (await db.scalars(
                select(Evaluation).where(Evaluation.interview_id.in_(interview_ids))
            )).all()
            eval_ids = [e.id for e in evals]

        async def _delete_all(rows: list[Any], label: str) -> None:
            n = 0
            for r in rows:
                try:
                    await db.delete(r)
                    n += 1
                except Exception as e:  # noqa: BLE001
                    errors.append(f"delete:{label}:{getattr(r, 'id', '?')}:{e}")
            deleted[label] = n

        ae_rows = (await db.scalars(
            select(AnswerEvaluation).where(AnswerEvaluation.evaluation_id.in_(eval_ids))
        )).all() if eval_ids else []
        fb_rows = (await db.scalars(
            select(RecruiterFeedback).where(RecruiterFeedback.interview_id.in_(interview_ids))
        )).all() if interview_ids else []
        coding_rows = (await db.scalars(
            select(CodingSubmission).where(CodingSubmission.interview_id.in_(interview_ids))
        )).all() if interview_ids else []
        proctor_rows = (await db.scalars(
            select(ProctoringEvent).where(ProctoringEvent.interview_id.in_(interview_ids))
        )).all() if interview_ids else []

        await _delete_all(ae_rows, "answer_evaluations")
        await _delete_all(fb_rows, "recruiter_feedback")
        if eval_ids:
            evals = (await db.scalars(
                select(Evaluation).where(Evaluation.id.in_(eval_ids))
            )).all()
            await _delete_all(evals, "evaluations")
        await _delete_all(answers, "answers")
        await _delete_all(coding_rows, "coding_submissions")
        await _delete_all(proctor_rows, "proctoring_events")
        await _delete_all(interviews, "interviews")
        await _delete_all(apps, "applications")
        await _delete_all([cand], "candidates")

        result["deleted_counts"] = deleted
    else:
        # ── Soft anonymize: scrub PII, keep aggregate-useful text ──────────
        if _is_anonymized(cand):
            result["anonymized"] = False
            result["skipped"] = "already_anonymized"
        else:
            cand.full_name = ANON_NAME
            cand.email = f"redacted+{candidate_id}@example.invalid"
            cand.phone = None
            cand.linkedin_url = None
            cand.portfolio_url = None
            for a in apps:
                a.cover_letter = None
                a.parsed_resume = None
                a.resume_s3_key = None
                a.resume_filename = None
            for iv in interviews:
                iv.recording_s3_key = None
            for a in answers:
                a.audio_s3_key = None
                sig = dict(a.ml_signals or {})
                sig["anonymized"] = True
                a.ml_signals = sig
            result["anonymized"] = True

    if errors:
        result["errors"] = errors

    db.add(AuditLog(
        org_id=org_id,
        action="gdpr_erase",
        resource_type="candidate",
        resource_id=candidate_id,
        log_metadata={
            "hard": hard,
            "storage_deleted": storage_deleted,
            "errors": len(errors),
            **({"deleted_counts": result.get("deleted_counts")} if hard else {}),
        },
    ))
    await db.commit()
    return result


async def purge_expired(
    retention_days: Optional[int] = None, org_id: Optional[str] = None
) -> dict:
    """Platform-wide (or org-scoped) retention job: anonymize candidates whose latest
    activity is older than retention. Idempotent — already-anonymized candidates are skipped.

    Uses its own AsyncSessionLocal so it can run standalone (Celery/beat) or per-org via routes.
    """
    days = retention_days if retention_days is not None else settings.GDPR_RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)

    processed = 0
    skipped = 0
    errors: list[str] = []

    async with AsyncSessionLocal() as db:
        q = select(Candidate).where(Candidate.created_at < cutoff)
        if org_id:
            q = q.where(Candidate.org_id == org_id)
        candidates = (await db.scalars(q)).all()

        for cand in candidates:
            # Skip already-anonymized (idempotent).
            if _is_anonymized(cand):
                skipped += 1
                continue
            # Determine latest activity: any application/interview newer than cutoff -> keep.
            latest = cand.created_at
            apps = (await db.scalars(
                select(Application.applied_at).where(Application.candidate_id == cand.id)
            )).all()
            ivs = (await db.scalars(
                select(Interview.created_at).where(Interview.candidate_id == cand.id)
            )).all()
            for ts in [*apps, *ivs]:
                if ts and ts > latest:
                    latest = ts
            if latest >= cutoff:
                skipped += 1
                continue
            try:
                await erase_candidate(db, cand.org_id, cand.id, hard=False)
                processed += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"{cand.id}:{e}")

    summary = {
        "ok": True,
        "retention_days": days,
        "cutoff": cutoff.isoformat(),
        "candidates_scanned": len(candidates),
        "anonymized": processed,
        "skipped": skipped,
        "org_id": org_id,
    }
    if errors:
        summary["errors"] = errors
    return summary
