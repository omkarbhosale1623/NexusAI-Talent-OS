"""Stripe billing — plan catalog, RBAC, checkout degradation, webhook."""
import hashlib
import hmac
import json
import time

from tests.conftest import signup, make_user, auth


async def test_plans_public_catalog(client):
    r = await client.get("/api/v1/billing/plans")
    assert r.status_code == 200
    body = r.json()
    keys = {p["plan"] for p in body["plans"]}
    assert keys == {"starter", "pro", "enterprise"}
    for p in body["plans"]:
        assert set(p) == {"plan", "name", "amount_cents", "interval", "features"}
        assert isinstance(p["amount_cents"], int)


async def test_checkout_requires_admin(client):
    r = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 401
    acc = await signup(client)
    recruiter = await make_user(acc["org_id"], "recruiter")
    r = await client.post("/api/v1/billing/checkout", json={"plan": "pro"},
                          headers=auth(recruiter))
    assert r.status_code == 403


async def test_checkout_unknown_plan_and_unconfigured(client):
    acc = await signup(client)
    r = await client.post("/api/v1/billing/checkout", json={"plan": "platinum"},
                          headers=auth(acc["token"]))
    assert r.status_code == 422
    # valid plan, but no STRIPE_SECRET_KEY in test env → graceful degradation
    r = await client.post("/api/v1/billing/checkout", json={"plan": "pro"},
                          headers=auth(acc["token"]))
    assert r.status_code == 200
    assert r.json() == {"ok": False, "reason": "billing_not_configured"}


async def test_webhook_rejects_bad_signature(client):
    from app.core.config import settings
    old = settings.STRIPE_WEBHOOK_SECRET
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    try:
        r = await client.post("/api/v1/billing/webhook", content=b"{}",
                              headers={"stripe-signature": "t=1,v1=bad"})
        assert r.status_code == 400
    finally:
        settings.STRIPE_WEBHOOK_SECRET = old


def _sign(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload,
                   hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


async def test_webhook_activates_plan(client):
    """Signed checkout.session.completed flips the tenant's plan."""
    from app.core.config import settings
    acc = await signup(client)
    event = {
        "id": "evt_test", "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"org_id": acc["org_id"], "plan": "pro"},
            "customer": "cus_test", "subscription": "sub_test",
        }},
    }
    payload = json.dumps(event).encode()
    old = settings.STRIPE_WEBHOOK_SECRET
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    try:
        r = await client.post(
            "/api/v1/billing/webhook", content=payload,
            headers={"stripe-signature": _sign(payload, "whsec_test"),
                     "content-type": "application/json"})
        assert r.status_code == 200, r.text
        assert r.json()["handled"] is True
    finally:
        settings.STRIPE_WEBHOOK_SECRET = old

    from app.core.database import AsyncSessionLocal
    from app.models.models import Tenant
    async with AsyncSessionLocal() as db:
        tenant = await db.get(Tenant, acc["org_id"])
        assert tenant.plan == "pro"
        assert tenant.settings["billing"]["stripe_subscription_id"] == "sub_test"
