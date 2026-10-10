"""Panel Service — multi-persona AI interview panel."""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.llm_service import LLMService

DEFAULT_PERSONAS: List[Dict[str, str]] = [
    {
        "name": "Maya",
        "role": "Engineering Manager",
        "persona": "pragmatic, focuses on system design & tradeoffs",
        "voice": "nova",
    },
    {
        "name": "Sam",
        "role": "People & Behavioral Lead",
        "persona": "warm but probing, focuses on collaboration, ownership & past behavior (STAR)",
        "voice": "shimmer",
    },
    {
        "name": "Dev",
        "role": "Domain Expert",
        "persona": "deeply technical, drills into domain depth, correctness & edge cases",
        "voice": "onyx",
    },
]


def resolve_personas(job) -> List[Dict[str, Any]]:
    """Return job-configured panel personas or the defaults."""
    personas = getattr(job, "panel_personas", None)
    if personas:
        return personas
    return DEFAULT_PERSONAS


def _ratio_spread(scores: List[float]) -> float:
    return (max(scores) - min(scores)) if scores else 0.0


async def panel_question(
    persona: Dict[str, Any],
    job_title: str,
    transcript_so_far: str,
    asked: List[str],
) -> str:
    """Generate ONE in-character interview question for a persona."""
    llm = LLMService()
    asked_block = "\n".join(f"- {q}" for q in asked) if asked else "(none yet)"
    system = (
        f"You are {persona.get('name')}, a {persona.get('role')} on an interview panel "
        f"for a {job_title} role. Your interviewing style: {persona.get('persona')}. "
        "Ask exactly ONE focused, in-character interview question. Stay in your lane "
        "and do not repeat anything already asked. Return only the question text."
    )
    user = (
        f"Interview transcript so far:\n{transcript_so_far or '(interview just started)'}\n\n"
        f"Questions already asked (avoid these):\n{asked_block}\n\n"
        "Now ask your single next question."
    )
    content, _model, _tokens = await llm.complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.8,
        max_tokens=200,
    )
    return (content or "").strip().strip('"')


async def panel_evaluate(
    personas: List[Dict[str, Any]],
    answers: List[Dict[str, Any]],
    job_title: str,
) -> Dict[str, Any]:
    """Each persona independently scores the candidate; aggregate into consensus."""
    llm = LLMService()
    transcript = "\n\n".join(
        f"Q: {a.get('question_text', '')}\nA: {a.get('answer_text', '')}"
        for a in answers
    ) or "(no answers recorded)"

    panel_scores: List[Dict[str, Any]] = []
    for persona in personas:
        system = (
            f"You are {persona.get('name')}, a {persona.get('role')} evaluating a candidate "
            f"for a {job_title} role. Your perspective: {persona.get('persona')}. "
            "Independently and critically score the candidate from your own viewpoint."
        )
        user = (
            f"Interview transcript:\n{transcript}\n\n"
            "Return JSON only with keys: "
            '{"score": <int 0-100>, "rating": "<one word>", "notes": "<2-3 sentences>", '
            '"strengths": [<strings>], "concerns": [<strings>]}'
        )
        content, _model, _tokens = await llm.complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=600,
            response_format="json",
        )
        data = llm._safe_json(content, {})
        try:
            score = float(data.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(100.0, score))
        panel_scores.append({
            "persona": persona.get("name"),
            "role": persona.get("role"),
            "score": round(score, 1),
            "rating": data.get("rating") or _rating_for(score),
            "notes": data.get("notes", ""),
            "strengths": data.get("strengths") or [],
            "concerns": data.get("concerns") or [],
        })

    scores = [p["score"] for p in panel_scores]
    consensus = round(sum(scores) / len(scores), 1) if scores else 0.0
    spread = _ratio_spread(scores)
    if spread <= 10:
        agreement = "high"
    elif spread <= 25:
        agreement = "mixed"
    else:
        agreement = "split"

    return {
        "panel_scores": panel_scores,
        "consensus_score": consensus,
        "consensus_recommendation": _recommendation_for(consensus),
        "agreement": agreement,
        "summary": (
            f"{len(panel_scores)} panelist(s) scored the candidate with an average of "
            f"{consensus}/100 ({agreement} agreement, spread {round(spread, 1)} pts)."
        ),
    }


def _rating_for(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "strong"
    if score >= 55:
        return "adequate"
    if score >= 40:
        return "weak"
    return "poor"


def _recommendation_for(score: float) -> str:
    if score >= 85:
        return "Strong Hire"
    if score >= 70:
        return "Hire"
    if score >= 50:
        return "Maybe"
    return "No Hire"
