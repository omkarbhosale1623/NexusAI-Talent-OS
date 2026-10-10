"""NexusAI Talent OS — FastAPI Application"""
import asyncio, time, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, get_logger
from app.core.redis_client import redis_client
from app.services.speech_service import prewarm_whisper, prewarm_tts_cache

logger = get_logger(__name__)
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"NexusAI Talent OS v{settings.APP_VERSION} starting [{settings.ENVIRONMENT}]")
    # Fail fast on insecure production configuration.
    from app.core.config import validate_production_secrets
    problems = validate_production_secrets()
    if problems:
        for p in problems:
            logger.error(f"INSECURE CONFIG: {p}")
        raise RuntimeError(
            "Refusing to start in production with insecure configuration: "
            + "; ".join(problems))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(prewarm_whisper())
    asyncio.create_task(prewarm_tts_cache())
    if settings.FEATURE_PROCTORING:
        try:
            from app.services.proctoring_service import prewarm_proctoring_models
            asyncio.create_task(prewarm_proctoring_models())
        except ImportError:
            logger.warning("Proctoring deps not installed — skipping pre-warm")
    try:
        await redis_client.ping(); logger.info("Redis OK")
    except Exception as e:
        logger.warning(f"Redis: {e}")
    yield
    await engine.dispose()
    await redis_client.close()

app = FastAPI(
    title="NexusAI Talent OS",
    description="The Operating System for Intelligent Hiring — by NexusAI",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None, lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
    expose_headers=["X-Request-ID","X-RateLimit-Remaining"])

from app.core.middleware import TenantMiddleware, RateLimitMiddleware, AuditMiddleware
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantMiddleware)

@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = rid
    t = time.perf_counter()
    resp: Response = await call_next(request)
    ms = (time.perf_counter() - t) * 1000
    resp.headers.update({"X-Request-ID": rid, "X-Response-Time": f"{ms:.2f}ms",
        "X-Powered-By":"NexusAI Talent OS","X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY",
        "Referrer-Policy":"strict-origin-when-cross-origin",
        "Permissions-Policy":"camera=(self), microphone=(self), geolocation=()"})
    if settings.REQUIRE_HTTPS:
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    logger.info("req", extra={"rid": rid, "method": request.method, "path": request.url.path,
        "status": resp.status_code, "ms": round(ms, 1)})
    return resp

@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"error": "internal_error",
        "message": "An unexpected error occurred",
        "request_id": getattr(request.state, "request_id", "")})

Instrumentator(should_ignore_untemplated=True,
    excluded_handlers=["/health","/metrics","/ready"]).instrument(app).expose(app, endpoint="/metrics")

# Register routers
from app.routes import auth, jobs, applications, interviews, scheduling
from app.routes import questions, evaluation, reports, candidates, speech, health, webhooks
# Feature modules (MVP)
from app.routes import (
    intelligence, recordings, coding, panel, benchmarks, ats,
    calendar, messaging, widget, orchestration, warehouse, learning,
    bulk, i18n, livekit, gdpr, billing,
)

V1 = "/api/v1"
app.include_router(health.router,       tags=["System"])
app.include_router(auth.router,         prefix=f"{V1}/auth",         tags=["Auth"])
app.include_router(jobs.router,         prefix=f"{V1}/jobs",         tags=["Jobs"])
app.include_router(applications.router, prefix=f"{V1}/applications", tags=["Applications"])
app.include_router(interviews.router,   prefix=f"{V1}/interviews",   tags=["Interviews"])
app.include_router(scheduling.router,   prefix=f"{V1}/schedule",     tags=["Scheduling"])
app.include_router(questions.router,    prefix=f"{V1}/questions",    tags=["Questions"])
app.include_router(evaluation.router,   prefix=f"{V1}/evaluation",   tags=["Evaluation"])
app.include_router(reports.router,      prefix=f"{V1}/reports",      tags=["Reports"])
app.include_router(candidates.router,   prefix=f"{V1}/candidates",   tags=["Candidates"])
app.include_router(speech.router,       prefix=f"{V1}/speech",       tags=["Speech"])
app.include_router(webhooks.router,     prefix=f"{V1}/webhooks",     tags=["Webhooks"])
# ── Feature modules ──────────────────────────────────────────────────────
# RBAC: routers that are purely back-office get role-gated at include time.
# Routers with public/candidate endpoints (intelligence, recordings, coding,
# panel, calendar callbacks, widget, i18n, livekit) enforce scoping per-route.
from fastapi import Depends
from app.core.authz import require_admin, require_staff
ADMIN = [Depends(require_admin)]   # org config / sensitive
STAFF = [Depends(require_staff)]   # recruiter+ back-office

app.include_router(intelligence.router, prefix=f"{V1}/intelligence", tags=["Intelligence"])
app.include_router(recordings.router,   prefix=f"{V1}/recordings",   tags=["Recordings"])
app.include_router(coding.router,       prefix=f"{V1}/coding",       tags=["Coding"])
app.include_router(panel.router,        prefix=f"{V1}/panel",        tags=["Panel"])
app.include_router(benchmarks.router,   prefix=f"{V1}/benchmarks",   tags=["Benchmarks"], dependencies=STAFF)
app.include_router(ats.router,          prefix=f"{V1}/ats",          tags=["ATS"], dependencies=ADMIN)
app.include_router(calendar.router,     prefix=f"{V1}/calendar",     tags=["Calendar"])
app.include_router(messaging.router,    prefix=f"{V1}/messaging",    tags=["Messaging"], dependencies=STAFF)
app.include_router(widget.router,       prefix=f"{V1}/widget",       tags=["Widget"])
app.include_router(orchestration.router,prefix=f"{V1}/orchestration",tags=["Orchestration"], dependencies=STAFF)
app.include_router(warehouse.router,    prefix=f"{V1}/warehouse",    tags=["Warehouse"], dependencies=ADMIN)
app.include_router(learning.router,     prefix=f"{V1}/learning",     tags=["Learning"], dependencies=STAFF)
app.include_router(bulk.router,         prefix=f"{V1}/bulk",         tags=["Bulk"], dependencies=STAFF)
app.include_router(i18n.router,         prefix=f"{V1}/i18n",         tags=["i18n"])
app.include_router(livekit.router,      prefix=f"{V1}/livekit",      tags=["LiveKit"])
app.include_router(gdpr.router,         prefix=f"{V1}/gdpr",         tags=["GDPR"])
app.include_router(billing.router,      prefix=f"{V1}/billing",      tags=["Billing"])
