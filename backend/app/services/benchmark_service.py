"""Benchmark Service — candidate vs cohort comparison (pure-python stats)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Evaluation, Interview


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs: List[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def _stddev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return var ** 0.5


def _percentile(xs: List[float], pct: float) -> float:
    """Linear-interpolation percentile; pct in [0, 100]."""
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    rank = (pct / 100.0) * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def _percentile_rank(xs: List[float], value: float) -> float:
    """Percent of cohort scoring <= value (inclusive), 0-100."""
    if not xs:
        return 0.0
    below = sum(1 for x in xs if x <= value)
    return round(100.0 * below / len(xs), 1)


def _cohort_stats(scores: List[float], candidate_score: float) -> Dict[str, Any]:
    count = len(scores)
    if count == 0:
        return {"count": 0, "note": "insufficient cohort"}
    stats: Dict[str, Any] = {
        "count": count,
        "mean": round(_mean(scores), 1),
        "median": round(_median(scores), 1),
        "stddev": round(_stddev(scores), 1),
        "min": round(min(scores), 1),
        "max": round(max(scores), 1),
        "p25": round(_percentile(scores, 25), 1),
        "p75": round(_percentile(scores, 75), 1),
        "percentile_rank": _percentile_rank(scores, candidate_score),
    }
    if count < 3:
        stats["note"] = "insufficient cohort"
    return stats


def _verdict(job_count: int, percentile_rank: float) -> str:
    if job_count < 3:
        return "insufficient cohort — benchmark is indicative only"
    if percentile_rank >= 90:
        return "top performer (top 10% of cohort)"
    if percentile_rank >= 75:
        return "above average"
    if percentile_rank >= 40:
        return "around the cohort average"
    if percentile_rank >= 20:
        return "below average"
    return "bottom of cohort"


async def cohort_benchmark(
    db: AsyncSession,
    interview_id: str,
    org_id: Optional[str],
) -> Dict[str, Any]:
    """Benchmark an interview's evaluation against job and org-wide cohorts."""
    ev_q = select(Evaluation).where(Evaluation.interview_id == interview_id)
    if org_id:
        ev_q = ev_q.where(Evaluation.org_id == org_id)
    target = await db.scalar(ev_q)
    if not target:
        return {"error": "evaluation not found", "interview_id": interview_id}

    candidate_score = float(target.overall_score or 0.0)

    # Resolve job_id for the job-level cohort.
    interview = await db.scalar(select(Interview).where(Interview.id == interview_id))
    job_id = getattr(interview, "job_id", None)

    # Org-wide cohort (all evaluations in org, or all if no org scoping).
    org_q = select(Evaluation)
    if org_id:
        org_q = org_q.where(Evaluation.org_id == org_id)
    org_evals = list((await db.scalars(org_q)).all())

    # Job-level cohort: same job within the org cohort.
    job_evals: List[Evaluation] = []
    if job_id:
        ids = {e.interview_id for e in org_evals}
        iv_q = select(Interview).where(Interview.job_id == job_id)
        if org_id:
            iv_q = iv_q.where(Interview.org_id == org_id)
        job_interview_ids = {i.id for i in (await db.scalars(iv_q)).all()}
        job_evals = [e for e in org_evals if e.interview_id in job_interview_ids and e.interview_id in ids]

    org_scores = [float(e.overall_score or 0.0) for e in org_evals]
    job_scores = [float(e.overall_score or 0.0) for e in job_evals]

    # Per-competency percentiles, computed against the job cohort (fallback org).
    comp_cohort = job_evals if len(job_evals) >= 3 else org_evals
    competency_percentiles: Dict[str, Any] = {}
    cand_comps = target.competency_scores or {}
    if isinstance(cand_comps, dict):
        for comp, val in cand_comps.items():
            try:
                cand_val = float(val)
            except (TypeError, ValueError):
                continue
            peer_vals: List[float] = []
            for e in comp_cohort:
                cs = e.competency_scores or {}
                if isinstance(cs, dict) and comp in cs:
                    try:
                        peer_vals.append(float(cs[comp]))
                    except (TypeError, ValueError):
                        pass
            competency_percentiles[comp] = {
                "candidate": round(cand_val, 1),
                "percentile_rank": _percentile_rank(peer_vals, cand_val) if peer_vals else None,
                "cohort_mean": round(_mean(peer_vals), 1) if peer_vals else None,
                "cohort_count": len(peer_vals),
            }

    job_stats = _cohort_stats(job_scores, candidate_score)
    org_stats = _cohort_stats(org_scores, candidate_score)

    return {
        "interview_id": interview_id,
        "job_id": job_id,
        "candidate_score": round(candidate_score, 1),
        "job_cohort": job_stats,
        "org_cohort": org_stats,
        "competency_percentiles": competency_percentiles,
        "verdict": _verdict(job_stats.get("count", 0), job_stats.get("percentile_rank", 0.0)),
    }
