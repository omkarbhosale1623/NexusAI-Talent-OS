"""NexusAI Talent OS — Coding interview routes.

Registered under prefix `/api/v1/coding`.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import CodingSubmission, Interview, Job
from app.services import code_exec_service

router = APIRouter()

SUPPORTED_LANGUAGES = frozenset(code_exec_service.PISTON_LANGUAGE_MAP)
MAX_SOURCE_CHARS = 100_000
MAX_STDIN_CHARS = 10_000
MAX_SUBMISSIONS_PER_INTERVIEW = 200


# ── inline schemas ─────────────────────────────────────────────────────────
class RunBody(BaseModel):
    language: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=MAX_SOURCE_CHARS)
    stdin: Optional[str] = Field(default="", max_length=MAX_STDIN_CHARS)
    problem_id: Optional[str] = Field(default=None, max_length=100)


class SubmitBody(BaseModel):
    language: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=MAX_SOURCE_CHARS)
    problem_id: str = Field(min_length=1, max_length=100)


class RunResult(BaseModel):
    submission_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    runtime_ms: int = 0
    provider: str = ""
    ok: bool = False


class SubmitResult(BaseModel):
    submission_id: str
    tests_passed: int
    tests_total: int
    score: float
    cases: list[dict] = []
    error: Optional[str] = None


class SubmissionOut(BaseModel):
    id: str
    interview_id: str
    problem_id: Optional[str] = None
    problem_title: Optional[str] = None
    language: str
    status: str
    score: Optional[float] = None
    tests_passed: int
    tests_total: int
    runtime_ms: Optional[int] = None
    created_at: Optional[str] = None


def _require_feature() -> None:
    if not settings.FEATURE_CODING:
        raise HTTPException(403, "Coding interviews are disabled")


def _require_language(language: str) -> None:
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            422, f"Unsupported language: {language}. Supported: {sorted(SUPPORTED_LANGUAGES)}")


async def _interview_for_exec(db: AsyncSession, interview_id: str) -> Interview:
    """Candidate-facing exec endpoints: interview must exist and still be open.
    The submission's org is derived from the interview (never a default)."""
    iv = await db.scalar(select(Interview).where(Interview.id == interview_id))
    if iv is None:
        raise HTTPException(404, "Interview not found")
    if iv.status in ("completed", "evaluated", "cancelled", "no_show"):
        raise HTTPException(409, "Interview is no longer accepting code submissions")
    count = await db.scalar(
        select(func.count()).select_from(CodingSubmission)
        .where(CodingSubmission.interview_id == interview_id))
    if (count or 0) >= MAX_SUBMISSIONS_PER_INTERVIEW:
        raise HTTPException(429, "Submission limit reached for this interview")
    return iv


def _public_problem(p: dict) -> dict:
    """Candidate-safe projection — never expose test cases / expected output."""
    return {
        "id": p.get("id"),
        "title": p.get("title"),
        "prompt": p.get("prompt"),
        "language_default": p.get("language_default"),
        "starter_code": p.get("starter_code"),
    }


# ── routes ─────────────────────────────────────────────────────────────────
@router.get("/problems")
async def get_problems(
    request: Request,
    job_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List problems. If `job_id` given, merge that Job's coding_config problems."""
    _require_feature()
    problems = code_exec_service.list_problems()
    if job_id:
        org_id = getattr(request.state, "org_id", None)
        stmt = select(Job).where(Job.id == job_id)
        if org_id:
            stmt = stmt.where(Job.org_id == org_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if job and job.coding_config:
            extra = job.coding_config.get("problems") or []
            ids = {p["id"] for p in problems}
            for p in extra:
                if isinstance(p, dict) and p.get("id") and p["id"] not in ids:
                    problems.append(_public_problem(p))
    return {"problems": problems}


@router.post("/{interview_id}/run", response_model=RunResult)
async def run(
    interview_id: str,
    body: RunBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Execute candidate code once and persist a 'ran' submission. Candidate-facing."""
    _require_feature()
    _require_language(body.language)
    iv = await _interview_for_exec(db, interview_id)
    org_id = iv.org_id
    result = await code_exec_service.run_code(body.language, body.source, body.stdin or "")

    problem = code_exec_service.get_problem(body.problem_id) if body.problem_id else None
    sub = CodingSubmission(
        interview_id=interview_id,
        org_id=org_id,
        problem_id=body.problem_id,
        problem_title=problem["title"] if problem else None,
        language=body.language,
        source_code=body.source,
        stdin=body.stdin or "",
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        exit_code=result.get("exit_code"),
        runtime_ms=result.get("runtime_ms"),
        status="ran",
    )
    db.add(sub)
    await db.flush()
    return RunResult(submission_id=sub.id, **{k: result[k] for k in
        ("stdout", "stderr", "exit_code", "runtime_ms", "provider", "ok")})


@router.post("/{interview_id}/submit", response_model=SubmitResult)
async def submit(
    interview_id: str,
    body: SubmitBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Run all tests for a problem and persist a scored 'submitted' submission. Candidate-facing."""
    _require_feature()
    _require_language(body.language)
    iv = await _interview_for_exec(db, interview_id)
    org_id = iv.org_id
    result = await code_exec_service.run_tests(body.language, body.source, body.problem_id)
    problem = code_exec_service.get_problem(body.problem_id)

    sub = CodingSubmission(
        interview_id=interview_id,
        org_id=org_id,
        problem_id=body.problem_id,
        problem_title=problem["title"] if problem else None,
        language=body.language,
        source_code=body.source,
        tests_passed=result.get("tests_passed", 0),
        tests_total=result.get("tests_total", 0),
        score=result.get("score"),
        status="submitted",
    )
    db.add(sub)
    await db.flush()
    # Candidate-facing response: per-case pass/fail + own stderr only —
    # expected outputs stay server-side so tests can't be hardcoded.
    cases = [
        {"passed": c.get("passed"), "stderr": c.get("stderr", "")}
        for c in result.get("cases", [])
    ]
    return SubmitResult(
        submission_id=sub.id,
        tests_passed=result.get("tests_passed", 0),
        tests_total=result.get("tests_total", 0),
        score=result.get("score", 0.0),
        cases=cases,
        error=result.get("error"),
    )


@router.get("/{interview_id}/submissions", response_model=list[SubmissionOut])
async def list_submissions(
    interview_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Org-scoped list of submissions for reviewers."""
    _require_feature()
    org_id = getattr(request.state, "org_id", None)
    stmt = select(CodingSubmission).where(CodingSubmission.interview_id == interview_id)
    if org_id:
        stmt = stmt.where(CodingSubmission.org_id == org_id)
    stmt = stmt.order_by(CodingSubmission.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [
        SubmissionOut(
            id=r.id,
            interview_id=r.interview_id,
            problem_id=r.problem_id,
            problem_title=r.problem_title,
            language=r.language,
            status=r.status,
            score=r.score,
            tests_passed=r.tests_passed,
            tests_total=r.tests_total,
            runtime_ms=r.runtime_ms,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
