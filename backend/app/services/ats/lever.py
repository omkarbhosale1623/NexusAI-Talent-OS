"""Lever API provider.

Auth: HTTP Basic with the API key as username and empty password.
Docs: https://hire.lever.co/developer/documentation
"""
from __future__ import annotations
from typing import Optional
import httpx
from app.core.config import settings
from app.services.ats.base import ATSProvider


class LeverProvider(ATSProvider):
    name = "lever"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        if not self.base_url:
            self.base_url = settings.LEVER_BASE_URL

    def _auth(self) -> dict:
        return {"auth": (self.api_key or "", "")}

    async def list_jobs(self) -> dict:
        try:
            async with self._client() as c:
                r = await c.get("/postings", params={"limit": 100})
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def list_candidates(self, job_id: Optional[str] = None) -> dict:
        try:
            params = {"limit": 100}
            if job_id:
                params["posting_id"] = job_id
            async with self._client() as c:
                r = await c.get("/opportunities", params=params)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    def _map_candidate(self, candidate: dict) -> dict:
        """NexusAI candidate dict → Lever candidate/opportunity payload."""
        payload: dict = {"name": (candidate.get("full_name") or "Candidate").strip()}
        if candidate.get("email"):
            payload["emails"] = [candidate["email"]]
        if candidate.get("phone"):
            payload["phones"] = [{"value": candidate["phone"]}]
        return payload

    async def push_candidate(self, candidate: dict) -> dict:
        try:
            payload = self._map_candidate(candidate)
            # Lever requires a perform_as user id for writes.
            params = {}
            perform_as = self.config.get("perform_as")
            if perform_as:
                params["perform_as"] = perform_as
            async with self._client() as c:
                r = await c.post("/candidates", json=payload, params=params)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def push_evaluation(self, candidate_ref: str, evaluation: dict) -> dict:
        """Post the NexusAI evaluation as a note on the Lever opportunity."""
        try:
            params = {}
            perform_as = self.config.get("perform_as")
            if perform_as:
                params["perform_as"] = perform_as
            body = {"value": _evaluation_summary(evaluation)}
            async with self._client() as c:
                r = await c.post(
                    f"/opportunities/{candidate_ref}/notes",
                    json=body,
                    params=params,
                )
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def test_connection(self) -> dict:
        try:
            async with self._client() as c:
                r = await c.get("/postings", params={"limit": 1})
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
