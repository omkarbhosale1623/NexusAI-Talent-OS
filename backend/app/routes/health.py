"""NexusAI Talent OS — Health Routes"""
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health():
    checks = {}
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    try:
        from app.core.redis_client import redis_client
        await redis_client.ping(); checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return HealthResponse(status=status, version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT, checks=checks)

@router.get("/ready")
async def ready():
    """Readiness probe — fails (503) if a critical dependency (DB) is down so
    Kubernetes stops routing traffic to this pod. Redis is treated as soft."""
    from fastapi import Response
    from app.core.database import engine
    from sqlalchemy import text
    checks = {}
    healthy = True
    try:
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["database"] = f"error: {e}"; healthy = False
    try:
        from app.core.redis_client import redis_client
        await redis_client.ping(); checks["redis"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["redis"] = f"degraded: {e}"  # soft dependency
    body = {"status": "ready" if healthy else "not_ready", "checks": checks}
    return body if healthy else Response(
        content=__import__("json").dumps(body), status_code=503,
        media_type="application/json")

@router.get("/live")
async def live(): return {"status": "alive"}
