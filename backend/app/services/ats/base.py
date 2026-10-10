"""ATS provider abstract base.

All provider methods are network-tolerant: every outbound HTTP call is wrapped
in try/except and returns a structured dict ``{ok, data}`` on success or
``{ok: False, error}`` on failure. Providers never raise on network errors.
"""
from __future__ import annotations
from typing import Any, Optional
import httpx


class ATSProvider:
    """Abstract base for ATS integrations.

    Subclasses are constructed with the org's ``ATSConnection`` row and read
    ``api_key`` / ``base_url`` / ``config`` from it.
    """

    name: str = "base"

    def __init__(self, connection: Any) -> None:
        from app.core.crypto import decrypt
        self.connection = connection
        # api_key is stored encrypted-at-rest; decrypt for outbound auth use.
        self.api_key: Optional[str] = decrypt(getattr(connection, "api_key", None))
        self.base_url: Optional[str] = getattr(connection, "base_url", None)
        self.config: dict = getattr(connection, "config", None) or {}

    # ── HTTP helpers ────────────────────────────────────────────────────────
    def _auth(self) -> dict:
        """Return kwargs (auth/headers) for httpx. Overridden per provider."""
        return {}

    def _client(self) -> httpx.AsyncClient:
        """Build an httpx.AsyncClient with auth + base_url configured."""
        kwargs: dict = {"timeout": 20.0}
        if self.base_url:
            kwargs["base_url"] = self.base_url.rstrip("/")
        kwargs.update(self._auth())
        return httpx.AsyncClient(**kwargs)

    @staticmethod
    def _ok(data: Any) -> dict:
        return {"ok": True, "data": data}

    @staticmethod
    def _err(error: str) -> dict:
        return {"ok": False, "error": error}

    # ── Abstract API ────────────────────────────────────────────────────────
    async def list_jobs(self) -> dict:
        raise NotImplementedError

    async def list_candidates(self, job_id: Optional[str] = None) -> dict:
        raise NotImplementedError

    async def push_candidate(self, candidate: dict) -> dict:
        raise NotImplementedError

    async def push_evaluation(self, candidate_ref: str, evaluation: dict) -> dict:
        raise NotImplementedError

    async def test_connection(self) -> dict:
        raise NotImplementedError
