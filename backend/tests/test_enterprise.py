"""Enterprise-hardening E2E + unit tests: RBAC, encryption-at-rest, GDPR,
prod-config validation. Run against a real (SQLite) DB via the `client` fixture."""
import pytest

from tests.conftest import signup, make_user, auth


# ── Encryption-at-rest (unit) ───────────────────────────────────────────────
def test_crypto_roundtrip_and_masking():
    from app.core.crypto import encrypt, decrypt, is_encrypted, mask_secret
    secret = "sk-live-ABCDEF1234567890"
    enc = encrypt(secret)
    assert is_encrypted(enc) and enc != secret
    assert decrypt(enc) == secret
    assert decrypt("legacy-plaintext") == "legacy-plaintext"   # passthrough
    assert mask_secret(enc).endswith("7890") and "ABCDEF" not in mask_secret(enc)
    assert encrypt(None) is None and encrypt("") == ""


def test_prod_secret_validation():
    from app.core.config import Settings, validate_production_secrets
    bad = Settings(ENVIRONMENT="production", JWT_SECRET="short",
                   DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
                   ENCRYPTION_KEY="", CORS_ORIGINS=["*"], DEBUG=True)
    problems = validate_production_secrets(bad)
    assert any("JWT_SECRET" in p for p in problems)
    assert any("ENCRYPTION_KEY" in p for p in problems)
    assert any("CORS" in p for p in problems)
    good = Settings(ENVIRONMENT="development")
    assert validate_production_secrets(good) == []


# ── RBAC enforcement (E2E) ──────────────────────────────────────────────────
async def test_rbac_admin_only_and_staff(client):
    me = await signup(client)
    admin_tok = me["token"]
    recruiter_tok = await make_user(me["org_id"], "recruiter")

    # Admin can reach an admin-only router (ATS)
    r = await client.get("/api/v1/ats/connections", headers=auth(admin_tok))
    assert r.status_code == 200, r.text

    # Recruiter is forbidden from the admin-only router
    r = await client.get("/api/v1/ats/connections", headers=auth(recruiter_tok))
    assert r.status_code == 403, r.text

    # Recruiter CAN reach a staff router (bulk)
    r = await client.get("/api/v1/bulk/status", headers=auth(recruiter_tok))
    assert r.status_code == 200, r.text

    # No token → 401
    r = await client.get("/api/v1/ats/connections")
    assert r.status_code == 401


# ── Encryption-at-rest wired through the ATS endpoint (E2E) ──────────────────
async def test_ats_api_key_encrypted_at_rest(client):
    me = await signup(client)
    tok = me["token"]
    plaintext = "ghkey-SUPERSECRET-9999"
    r = await client.post("/api/v1/ats/connections", headers=auth(tok),
                          json={"provider": "greenhouse", "api_key": plaintext})
    assert r.status_code == 200, r.text
    # Response is masked, never the raw key
    assert plaintext not in r.text

    # The stored column must be ciphertext (enc:: prefix), decryptable back
    from app.core.database import AsyncSessionLocal
    from app.models.models import ATSConnection
    from app.core.crypto import is_encrypted, decrypt
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        conn = await db.scalar(select(ATSConnection).where(
            ATSConnection.org_id == me["org_id"]))
    assert conn is not None
    assert is_encrypted(conn.api_key) and conn.api_key != plaintext
    assert decrypt(conn.api_key) == plaintext


# ── GDPR export + erasure (E2E) ─────────────────────────────────────────────
async def _make_candidate(org_id: str) -> str:
    from app.core.database import AsyncSessionLocal
    from app.models.models import Candidate
    async with AsyncSessionLocal() as db:
        cand = Candidate(org_id=org_id, full_name="Jane Doe",
                         email="jane@example.com", phone="+15555550100")
        db.add(cand)
        await db.commit()
        return cand.id


async def test_gdpr_export_and_erase(client):
    me = await signup(client)
    tok = me["token"]
    cand_id = await _make_candidate(me["org_id"])

    # Export (staff allowed)
    r = await client.get(f"/api/v1/gdpr/candidates/{cand_id}/export", headers=auth(tok))
    assert r.status_code == 200, r.text
    assert "jane@example.com" in r.text

    # Erase / anonymize (admin)
    r = await client.post(f"/api/v1/gdpr/candidates/{cand_id}/erase",
                          headers=auth(tok), json={"hard": False})
    assert r.status_code == 200, r.text

    # PII must be gone afterwards
    from app.core.database import AsyncSessionLocal
    from app.models.models import Candidate
    async with AsyncSessionLocal() as db:
        cand = await db.get(Candidate, cand_id)
    assert cand is not None
    assert cand.full_name != "Jane Doe"
    assert "jane@example.com" not in (cand.email or "")
    assert cand.phone in (None, "")


async def test_gdpr_policy_public_shape(client):
    me = await signup(client)
    r = await client.get("/api/v1/gdpr/policy", headers=auth(me["token"]))
    assert r.status_code == 200
    body = r.json()
    assert "retention_days" in str(body) or "retention" in str(body).lower()
