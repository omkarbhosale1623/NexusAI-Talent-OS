"""Pytest fixtures — hermetic test config (SQLite, no Redis/whisper).
Env MUST be set before any `app.*` import so Settings picks it up."""
import os
import warnings

warnings.filterwarnings("ignore")

from cryptography.fernet import Fernet  # noqa: E402

_DB = os.path.join(os.path.dirname(__file__), "_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_DB}")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("FEATURE_PROCTORING", "false")
os.environ.setdefault("EMAIL_ENABLED", "false")
os.environ.setdefault("JWT_SECRET", "test-secret-key-0123456789abcdef0123456789")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def client():
    """Fresh schema + ASGI client (no lifespan → no model downloads/Redis)."""
    if os.path.exists(_DB):
        os.remove(_DB)
    from app.main import app
    from app.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


async def signup(c, company="Acme") -> dict:
    """Create a tenant + admin and return {token, org_id, user_id}."""
    import secrets
    r = await c.post("/api/v1/auth/signup", json={
        "email": f"admin-{secrets.token_hex(4)}@acmecorp.io",
        "password": "Passw0rd!23456", "full_name": "Admin", "company_name": company})
    assert r.status_code == 200, r.text
    return r.json()


async def make_user(org_id: str, role: str) -> str:
    """Insert a user with a given role + a session token; return the raw token."""
    import hashlib
    import secrets
    from datetime import datetime, timedelta
    from app.core.database import AsyncSessionLocal
    from app.models.models import User, AuthSession
    from app.routes.auth import hash_password
    async with AsyncSessionLocal() as db:
        u = User(org_id=org_id, email=f"{role}-{secrets.token_hex(4)}@acmecorp.io",
                 password_hash=hash_password("x"), full_name=role.title(), role=role)
        db.add(u)
        await db.flush()
        raw = secrets.token_urlsafe(32)
        db.add(AuthSession(
            user_id=u.id, org_id=org_id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(hours=1)))
        await db.commit()
        return raw


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
