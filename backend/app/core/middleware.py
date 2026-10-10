"""NexusAI Talent OS — Auth/Tenant Middleware + Rate Limiting + Audit"""
import hashlib, time
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from app.core.config import settings

PUBLIC_PATHS = {
    "/health", "/ready", "/live", "/metrics", "/docs", "/openapi.json",
    "/api/v1/auth/signup", "/api/v1/auth/login",
    "/api/v1/billing/plans",     # public pricing catalog
    "/api/v1/billing/webhook",   # Stripe server-to-server (signature-verified)
}
# These prefixes are public ONLY for safe (GET/HEAD) methods — e.g. the public
# job board. Writes (POST/PATCH/DELETE) still require admin auth so the route's
# request.state.org_id is always populated.
PUBLIC_GET_PREFIXES = (
    "/api/v1/jobs",                      # public job listing/detail
)
PUBLIC_PREFIXES = (
    "/api/v1/applications/jobs/",         # apply endpoint
    "/api/v1/interviews/by-token/",
    "/api/v1/candidates/portal/",
    "/api/v1/schedule/by-schedule-token/",
    "/api/v1/schedule/book/",
    "/api/v1/speech/",                    # candidate uses speech without admin auth
    "/api/v1/widget/",                    # white-label embed — cross-origin, public
    "/api/v1/i18n/locales",              # public locale list
    "/api/v1/i18n/bundle/",             # public translation bundles
    "/api/v1/calendar/google/callback",  # OAuth redirect (org derived from state)
    "/api/v1/calendar/outlook/callback",
)

# Candidate-facing feature endpoints: auth is OPTIONAL (token attached if present,
# org_id left None otherwise — routes handle the None case and scope by interview).
OPTIONAL_AUTH_SUFFIXES = (
    "/fraud-event", "/upload", "/run", "/submit", "/token", "/translate",
)
OPTIONAL_AUTH_EXACT = (
    "/api/v1/coding/problems",
)

class TenantMiddleware(BaseHTTPMiddleware):
    """Injects org_id + user_id into request.state from Bearer token.
    Public/candidate-facing routes skip auth entirely."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # GET-only public prefixes (job board): writes fall through to auth.
        if request.method in ("GET", "HEAD") and any(
            path.startswith(p) for p in PUBLIC_GET_PREFIXES
        ):
            return await call_next(request)

        # Interview conversation/start/complete endpoints are used by BOTH
        # admin (testing) and candidates (no token) — allow optional auth
        if "/interviews/" in path and (
            path.endswith("/conversation") or path.endswith("/start") or path.endswith("/complete")
        ):
            await self._try_attach_org(request)
            return await call_next(request)

        # Candidate-facing feature endpoints (panel question, coding run/submit,
        # recording upload, fraud event, livekit token, i18n translate) — optional auth
        if path in OPTIONAL_AUTH_EXACT or path.endswith(OPTIONAL_AUTH_SUFFIXES):
            await self._try_attach_org(request)
            return await call_next(request)

        raw = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not raw:
            return JSONResponse({"error": "unauthorized", "message": "Missing token"}, status_code=401)

        from app.core.database import AsyncSessionLocal
        from app.models.models import AuthSession, User
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        async with AsyncSessionLocal() as db:
            session = await db.scalar(
                select(AuthSession).where(AuthSession.token_hash == token_hash, AuthSession.revoked == False)
            )
            if not session or session.expires_at < datetime.utcnow():
                return JSONResponse({"error": "unauthorized", "message": "Invalid or expired token"}, status_code=401)
            request.state.org_id = session.org_id
            request.state.user_id = session.user_id
            user = await db.get(User, session.user_id)
            request.state.role = user.role if user else "recruiter"
            if user and not user.is_active:
                return JSONResponse({"error": "forbidden", "message": "Account disabled"}, status_code=403)

        return await call_next(request)

    async def _try_attach_org(self, request: Request):
        """For mixed public/private endpoints — attach org_id if token present, else leave None."""
        raw = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        request.state.org_id = None
        request.state.user_id = None
        request.state.role = None
        if not raw: return
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.models import AuthSession, User
            token_hash = hashlib.sha256(raw.encode()).hexdigest()
            async with AsyncSessionLocal() as db:
                session = await db.scalar(
                    select(AuthSession).where(AuthSession.token_hash == token_hash, AuthSession.revoked == False)
                )
                if session and session.expires_at >= datetime.utcnow():
                    request.state.org_id = session.org_id
                    request.state.user_id = session.user_id
                    user = await db.get(User, session.user_id)
                    request.state.role = user.role if user else "recruiter"
        except Exception:
            pass


class RateLimitMiddleware(BaseHTTPMiddleware):
    LIMITS = {
        "/api/v1/auth/login": (10, 60), "/api/v1/auth/signup": (5, 60),
        "/api/v1/speech/transcribe": (60, 60), "/api/v1/interviews": (20, 60),
        "/api/v1/i18n/translate": (20, 60),   # public LLM endpoint — keep tight
        "default": (300, 60),
    }
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        try:
            from app.core.redis_client import redis_client
            path = request.url.path
            limit, window = self.LIMITS.get(path, self.LIMITS["default"])
            ip = request.client.host if request.client else "unknown"
            key = f"rl:{hashlib.md5(f'{ip}:{path}'.encode()).hexdigest()}"
            now = time.time()
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key); pipe.zadd(key, {str(now): now}); pipe.expire(key, window + 10)
            results = await pipe.execute()
            if results[1] >= limit:
                return JSONResponse({"error": "rate_limit_exceeded", "message": "Too many requests"},
                    status_code=429, headers={"Retry-After": str(window)})

            # Per-tenant global limit (fair-use across an org's whole API surface)
            org_id = getattr(request.state, "org_id", None)
            tlimit = settings.RATE_LIMIT_PER_TENANT
            if org_id and tlimit > 0:
                tkey = f"rlt:{org_id}"
                tpipe = redis_client.pipeline()
                tpipe.zremrangebyscore(tkey, 0, now - 60)
                tpipe.zcard(tkey); tpipe.zadd(tkey, {str(now): now}); tpipe.expire(tkey, 70)
                tres = await tpipe.execute()
                if tres[1] >= tlimit:
                    return JSONResponse(
                        {"error": "tenant_rate_limit_exceeded",
                         "message": "Organization request quota exceeded"},
                        status_code=429, headers={"Retry-After": "60"})
        except Exception:
            pass
        return await call_next(request)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not settings.AUDIT_LOG_ENABLED or request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.models import AuditLog
            parts = request.url.path.split("/")
            async with AsyncSessionLocal() as db:
                db.add(AuditLog(
                    org_id=getattr(request.state, "org_id", None),
                    user_id=getattr(request.state, "user_id", None),
                    action=request.method,
                    resource_type=parts[3] if len(parts) > 3 else "unknown",
                    resource_id=parts[4] if len(parts) > 4 else None,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", "")[:500],
                    log_metadata={"status_code": response.status_code},
                ))
                await db.commit()
        except Exception:
            pass
        return response
