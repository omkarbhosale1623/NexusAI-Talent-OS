"""Multi-agent interview/evaluation orchestration.

LangGraph StateGraph when available + FEATURE_LANGGRAPH; otherwise a pure-async
sequential 3-stage chain. Both paths use LLMService and return the same shape.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# ── lazy optional dep ────────────────────────────────────────────────────────
try:
    from langgraph.graph import StateGraph, END  # type: ignore
    _LANGGRAPH = True
except ImportError:  # pragma: no cover - optional dep
    StateGraph = None  # type: ignore
    END = None  # type: ignore
    _LANGGRAPH = False


def graph_available() -> bool:
    return _LANGGRAPH and bool(settings.FEATURE_LANGGRAPH)


def _transcript(answers: List[Dict]) -> str:
    parts = []
    for i, a in enumerate(answers, 1):
        q = a.get("question_text") or a.get("question") or ""
        ans = a.get("answer_text") or a.get("answer") or ""
        parts.append(f"Q{i}: {q}\nA{i}: {ans}")
    return "\n\n".join(parts)


# ── agent stages (shared by both engines) ────────────────────────────────────
async def _screen(llm: LLMService, session_data: Dict, answers: List[Dict]) -> Dict:
    """Stage 1 — quick screen / fit signal."""
    prompt = (
        "You are a recruiting screener. Given the interview transcript, judge "
        "overall fit briefly. Return JSON: "
        '{"fit":"strong|moderate|weak","signals":[],"concerns":[]}\n\n'
        f"Candidate: {session_data.get('candidate_name','N/A')}\n"
        f"Role: {session_data.get('candidate_role','N/A')}\n\n"
        f"{_transcript(answers)[:4000]}"
    )
    content, _, _ = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2, max_tokens=600, response_format="json",
    )
    return llm._safe_json(content, {"fit": "moderate", "signals": [], "concerns": []})


async def _question_planner(llm: LLMService, session_data: Dict,
                            answers: List[Dict], screen: Dict) -> Dict:
    """Stage 2 — derive focus areas / probes from the screen output."""
    prompt = (
        "You plan evaluation focus. Given a screen result, list the competency "
        "dimensions to weight and any follow-up probes. Return JSON: "
        '{"focus_dimensions":[],"probes":[],"rationale":""}\n\n'
        f"Screen fit: {screen.get('fit')}\n"
        f"Concerns: {screen.get('concerns')}\n"
        f"Role: {session_data.get('candidate_role','N/A')}"
    )
    content, _, _ = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=600, response_format="json",
    )
    return llm._safe_json(content, {"focus_dimensions": [], "probes": [], "rationale": ""})


async def _evaluator(llm: LLMService, session_data: Dict,
                     answers: List[Dict], plan: Dict) -> Dict:
    """Stage 3 — full rigorous evaluation, focus-aware."""
    focus = ", ".join(plan.get("focus_dimensions", [])) or "technical, communication, behavioral"
    prompt = (
        "You are an expert interview evaluator. Evaluate the transcript with "
        f"emphasis on: {focus}. Return JSON: "
        '{"overall_score":0-100,"recommendation":"Strong Hire|Hire|Consider|No Hire",'
        '"competency_scores":{},"summary":"3-4 sentences"}\n\n'
        f"Candidate: {session_data.get('candidate_name','N/A')}\n"
        f"Role: {session_data.get('candidate_role','N/A')}\n\n"
        f"{_transcript(answers)[:5000]}"
    )
    content, _, _ = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=1500, response_format="json",
    )
    return llm._safe_json(content, {})


def _aggregate(screen: Dict, plan: Dict, evaluation: Dict) -> Dict:
    score = evaluation.get("overall_score")
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    rec = evaluation.get("recommendation") or "Consider"
    summary = evaluation.get("summary") or ""
    return {"overall_score": score, "recommendation": rec, "summary": summary}


# ── public entry — works with or without langgraph ───────────────────────────
async def run_evaluation_pipeline(session_data: Dict, answers: List[Dict]) -> Dict:
    llm = LLMService()
    if graph_available():
        try:
            return await _run_langgraph(llm, session_data, answers)
        except Exception as exc:  # degrade gracefully
            logger.warning(f"langgraph pipeline failed, falling back: {exc}")
    return await _run_sequential(llm, session_data, answers)


async def _run_sequential(llm: LLMService, session_data: Dict,
                          answers: List[Dict]) -> Dict:
    screen = await _screen(llm, session_data, answers)
    plan = await _question_planner(llm, session_data, answers, screen)
    evaluation = await _evaluator(llm, session_data, answers, plan)
    final = _aggregate(screen, plan, evaluation)
    return {
        "stages": {"screen": screen, "question_planner": plan, "evaluator": evaluation},
        "final": final,
        "engine": "sequential",
    }


async def _run_langgraph(llm: LLMService, session_data: Dict,
                         answers: List[Dict]) -> Dict:
    graph = _build_graph(llm)
    state: Dict[str, Any] = {"session_data": session_data, "answers": answers}
    out = await graph.ainvoke(state)
    final = _aggregate(out.get("screen", {}), out.get("plan", {}), out.get("evaluation", {}))
    return {
        "stages": {
            "screen": out.get("screen", {}),
            "question_planner": out.get("plan", {}),
            "evaluator": out.get("evaluation", {}),
        },
        "final": final,
        "engine": "langgraph",
    }


def _build_graph(llm: LLMService):
    """Build a StateGraph: screen → question_planner → evaluator → aggregator."""
    sg = StateGraph(dict)  # type: ignore

    async def screen_node(state: Dict) -> Dict:
        state["screen"] = await _screen(llm, state["session_data"], state["answers"])
        return state

    async def planner_node(state: Dict) -> Dict:
        state["plan"] = await _question_planner(
            llm, state["session_data"], state["answers"], state["screen"])
        return state

    async def evaluator_node(state: Dict) -> Dict:
        state["evaluation"] = await _evaluator(
            llm, state["session_data"], state["answers"], state["plan"])
        return state

    async def aggregator_node(state: Dict) -> Dict:
        state["final"] = _aggregate(
            state.get("screen", {}), state.get("plan", {}), state.get("evaluation", {}))
        return state

    sg.add_node("screen", screen_node)
    sg.add_node("question_planner", planner_node)
    sg.add_node("evaluator", evaluator_node)
    sg.add_node("aggregator", aggregator_node)
    sg.set_entry_point("screen")
    sg.add_edge("screen", "question_planner")
    sg.add_edge("question_planner", "evaluator")
    sg.add_edge("evaluator", "aggregator")
    sg.add_edge("aggregator", END)
    return sg.compile()
