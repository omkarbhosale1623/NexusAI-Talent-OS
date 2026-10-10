"""Workday provider — documented stub.

Workday integrations are highly tenant-specific: each customer exposes its own
REST/SOAP endpoints, object model, and OAuth/bearer credentials. There is no
single public "Workday API" we can target generically.

This provider therefore:
  * Returns a clear "needs configuration" error when ``base_url`` is unset.
  * When ``base_url`` IS configured, attempts a *generic* bearer-token REST call
    against tenant-provided paths (overridable via ``config``):
        config = {
            "jobs_path": "/jobRequisitions",
            "candidates_path": "/candidates",
            "push_candidate_path": "/candidates",
            "push_evaluation_path": "/candidates/{ref}/notes",
            "test_path": "/jobRequisitions",
        }
All network calls are wrapped and return structured ``{ok, error}``.
"""
from __future__ import annotations
from typing import Optional
import httpx
from app.core.config import settings
from app.services.ats.base import ATSProvider

_NOT_CONFIGURED = "Workday requires tenant-specific configuration"


class WorkdayProvider(ATSProvider):
    name = "workday"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        if not self.base_url:
            self.base_url = settings.WORKDAY_BASE_URL or None

    def _configured(self) -> bool:
        return bool(self.base_url)

    def _auth(self) -> dict:
        return {"headers": {"Authorization": f"Bearer {self.api_key or ''}"}}

    def _path(self, key: str, default: str) -> str:
        return self.config.get(key, default)

    async def list_jobs(self) -> dict:
        if not self._configured():
            return self._err(_NOT_CONFIGURED)
        try:
            async with self._client() as c:
                r = await c.get(self._path("jobs_path", "/jobRequisitions"))
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def list_candidates(self, job_id: Optional[str] = None) -> dict:
        if not self._configured():
            return self._err(_NOT_CONFIGURED)
        try:
            params = {"jobRequisitionId": job_id} if job_id else None
            async with self._client() as c:
                r = await c.get(self._path("candidates_path", "/candidates"), params=params)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    def _map_candidate(self, candidate: dict) -> dict:
        return {
            "name": (candidate.get("full_name") or "Candidate").strip(),
            "email": candidate.get("email"),
            "phone": candidate.get("phone"),
        }

    async def push_candidate(self, candidate: dict) -> dict:
        if not self._configured():
            return self._err(_NOT_CONFIGURED)
        try:
            payload = self._map_candidate(candidate)
            async with self._client() as c:
                r = await c.post(self._path("push_candidate_path", "/candidates"), json=payload)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def push_evaluation(self, candidate_ref: str, evaluation: dict) -> dict:
        if not self._configured():
            return self._err(_NOT_CONFIGURED)
        try:
            path = self._path("push_evaluation_path", "/candidates/{ref}/notes").replace(
                "{ref}", str(candidate_ref)
            )
            body = {
                "note": _evaluation_summary(evaluation),
                "overall_score": evaluation.get("overall_score"),
                "recommendation": evaluation.get("recommendation"),
            }
            async with self._client() as c:
                r = await c.post(path, json=body)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def test_connection(self) -> dict:
        if not self._configured():
            return self._err(_NOT_CONFIGURED)
        try:
            async with self._client() as c:
                r = await c.get(self._path("test_path", "/jobRequisitions"))
                r.raise_for_status()
                return self._ok({"status": "connected"})
        except httpx.HTTPStatusError as e:
            return self._err(f"HTTP {e.response.status_code}")
        except Exception as e:
            return self._err(str(e))


def _evaluation_summary(evaluation: dict) -> str:
    score = evaluation.get("overall_score")
    rec = evaluation.get("recommendation")
    parts = ["NexusAI Talent OS evaluation"]
    if score is not None:
        parts.append(f"Overall score: {score}")
    if rec:
        parts.append(f"Recommendation: {rec}")
    summary = evaluation.get("executive_summary")
    if summary:
        parts.append(summary)
    return "\n".join(parts)
