"""Greenhouse Harvest API provider.

Auth: HTTP Basic with the API key as username and empty password.
Docs: https://developers.greenhouse.io/harvest.html
"""
from __future__ import annotations
from typing import Optional
import httpx
from app.core.config import settings
from app.services.ats.base import ATSProvider


class GreenhouseProvider(ATSProvider):
    name = "greenhouse"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        if not self.base_url:
            self.base_url = settings.GREENHOUSE_BASE_URL

    def _auth(self) -> dict:
        # Basic auth: api_key as username, empty password.
        return {"auth": (self.api_key or "", "")}

    async def list_jobs(self) -> dict:
        try:
            async with self._client() as c:
                r = await c.get("/jobs", params={"per_page": 100})
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def list_candidates(self, job_id: Optional[str] = None) -> dict:
        try:
            params = {"per_page": 100}
            if job_id:
                params["job_id"] = job_id
            async with self._client() as c:
                r = await c.get("/candidates", params=params)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    def _map_candidate(self, candidate: dict) -> dict:
        """NexusAI candidate dict → Greenhouse candidate payload."""
        full_name = (candidate.get("full_name") or "").strip()
        first, _, last = full_name.partition(" ")
        payload: dict = {
            "first_name": first or full_name or "Candidate",
            "last_name": last or "",
        }
        if candidate.get("email"):
            payload["email_addresses"] = [
                {"value": candidate["email"], "type": "personal"}
            ]
        if candidate.get("phone"):
            payload["phone_numbers"] = [
                {"value": candidate["phone"], "type": "mobile"}
            ]
        notes = candidate.get("notes")
        if notes:
            payload["notes"] = notes
        return payload

    async def push_candidate(self, candidate: dict) -> dict:
        try:
            payload = self._map_candidate(candidate)
            headers = {}
            # Greenhouse requires On-Behalf-Of for POST; allow via config.
            on_behalf = self.config.get("on_behalf_of")
            if on_behalf:
                headers["On-Behalf-Of"] = str(on_behalf)
            async with self._client() as c:
                r = await c.post("/candidates", json=payload, headers=headers)
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def push_evaluation(self, candidate_ref: str, evaluation: dict) -> dict:
        """Attach the NexusAI evaluation as a note on the Greenhouse candidate."""
        try:
            on_behalf = self.config.get("on_behalf_of")
            if not on_behalf:
                return self._err("Greenhouse note requires config.on_behalf_of (user id)")
            body = {
                "user_id": int(on_behalf),
                "body": _evaluation_summary(evaluation),
                "visibility": "public",
            }
            headers = {"On-Behalf-Of": str(on_behalf)}
            async with self._client() as c:
                r = await c.post(
                    f"/candidates/{candidate_ref}/activity_feed/notes",
                    json=body,
                    headers=headers,
                )
                r.raise_for_status()
                return self._ok(r.json())
        except Exception as e:
            return self._err(str(e))

    async def test_connection(self) -> dict:
        try:
            async with self._client() as c:
                r = await c.get("/jobs", params={"per_page": 1})
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
