"""
Resilient outbound HTTP client for third-party integrations (ATS, calendar,
code-exec, SMS). Adds: connect/read timeouts, bounded retries with exponential
backoff + jitter on transient errors (network / 429 / 5xx), and a lightweight
per-host circuit breaker so a flapping provider can't exhaust workers.

No external deps (no tenacity) — keeps the import graph light.
"""
import asyncio
import logging
import random
import time
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_STATUS = {429, 500, 502, 503, 504}

# host -> (failure_count, open_until_epoch)
_breakers: dict[str, tuple[int, float]] = {}
_BREAKER_THRESHOLD = 5
_BREAKER_COOLDOWN_S = 30.0


def _breaker_open(host: str) -> bool:
    fails, open_until = _breakers.get(host, (0, 0.0))
    return open_until > time.monotonic()


def _record(host: str, ok: bool) -> None:
    fails, _ = _breakers.get(host, (0, 0.0))
    if ok:
        _breakers.pop(host, None)
    else:
        fails += 1
        open_until = time.monotonic() + _BREAKER_COOLDOWN_S if fails >= _BREAKER_THRESHOLD else 0.0
        _breakers[host] = (fails, open_until)


def client(timeout: Optional[float] = None, **kwargs) -> httpx.AsyncClient:
    """Create an AsyncClient with sane enterprise defaults."""
    t = timeout if timeout is not None else settings.HTTP_TIMEOUT
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    return httpx.AsyncClient(
        timeout=httpx.Timeout(t, connect=min(5.0, t)),
        limits=limits,
        follow_redirects=True,
        **kwargs,
    )


async def request(method: str, url: str, *, retries: Optional[int] = None,
                  **kwargs) -> httpx.Response:
    """
    Perform an HTTP request with retries + circuit breaking.
    Raises httpx.HTTPError after exhausting retries; callers should try/except.
    """
    host = httpx.URL(url).host or url
    if _breaker_open(host):
        raise httpx.ConnectError(f"circuit open for {host}")

    attempts = (retries if retries is not None else settings.HTTP_RETRIES) + 1
    last_exc: Optional[Exception] = None
    async with client() as c:
        for i in range(attempts):
            try:
                resp = await c.request(method, url, **kwargs)
                if resp.status_code in _RETRY_STATUS and i < attempts - 1:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}", request=resp.request, response=resp)
                _record(host, ok=True)
                return resp
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                _record(host, ok=False)
                if i < attempts - 1:
                    backoff = min(8.0, 0.4 * (2 ** i)) + random.uniform(0, 0.3)
                    logger.warning("HTTP %s %s failed (attempt %d/%d): %s; retrying in %.1fs",
                                   method, host, i + 1, attempts, exc, backoff)
                    await asyncio.sleep(backoff)
    assert last_exc is not None
    raise last_exc


async def get(url: str, **kwargs) -> httpx.Response:
    return await request("GET", url, **kwargs)


async def post(url: str, **kwargs) -> httpx.Response:
    return await request("POST", url, **kwargs)