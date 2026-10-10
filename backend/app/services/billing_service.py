"""NexusAI Talent OS — Stripe billing for plans & pricing.

Optional dependency: ``stripe`` is imported lazily. When the SDK or the
``STRIPE_SECRET_KEY`` is unavailable, every call degrades to
``{ok: False, reason}`` — the same pattern as the LiveKit/ATS integrations.

Plan state lives on the tenant: ``tenants.plan`` (free|starter|pro|enterprise)
plus Stripe customer/subscription ids under ``tenants.settings["billing"]``.
Amounts are integers in cents — never floats.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Tenant

logger = logging.getLogger(__name__)

# Catalog mirrors docs/PRD.md pricing. Amounts in USD cents / month.
PLANS: dict[str, dict] = {
    "starter": {
        "name": "Starter",
        "amount_cents": 50000,          # $500/mo
        "interval": "month",
        "features": ["50 interviews/mo", "2 rounds", "Text report"],
    },
    "pro": {
        "name": "Pro",
        "amount_cents": 200000,         # $2,000/mo
        "interval": "month",
        "features": ["200 interviews/mo", "4 rounds", "Video proctoring",
                     "PDF reports", "Analytics"],
    },
    "enterprise": {
        "name": "Enterprise",
        "amount_cents": 300000,         # $3,000/mo (+ setup, invoiced separately)
        "interval": "month",
        "features": ["Unlimited interviews", "Custom rubrics", "ATS integration",
                     "White-label", "Dedicated support"],
    },
}

_PRICE_ID_SETTINGS = {
    "starter": "STRIPE_PRICE_STARTER",
    "pro": "STRIPE_PRICE_PRO",
    "enterprise": "STRIPE_PRICE_ENTERPRISE",
}


def billing_available() -> bool:
    """True only when the feature flag and the Stripe secret key are set."""
    return bool(settings.FEATURE_BILLING and settings.STRIPE_SECRET_KEY)


def _stripe():
    """Lazy import; returns the configured stripe module or None."""
    try:
        import stripe  # type: ignore
    except ImportError:
        return None
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def plan_catalog() -> list[dict]:
    """Public pricing catalog (no Stripe ids/secrets)."""
    return [
        {"plan": key, "name": p["name"], "amount_cents": p["amount_cents"],
         "interval": p["interval"], "features": p["features"]}
        for key, p in PLANS.items()
    ]


async def create_checkout_session(db: AsyncSession, org_id: str, plan: str) -> dict:
    """Create a Stripe Checkout session for a subscription to `plan`."""
    if plan not in PLANS:
        return {"ok": False, "reason": f"unknown plan: {plan}"}
    if not billing_available():
        return {"ok": False, "reason": "billing_not_configured"}
    stripe = _stripe()
    if stripe is None:
        return {"ok": False, "reason": "stripe_sdk_not_installed"}

    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        return {"ok": False, "reason": "organization not found"}

    price_id = getattr(settings, _PRICE_ID_SETTINGS[plan], "")
    if price_id:
        line_item = {"price": price_id, "quantity": 1}
    else:
        p = PLANS[plan]
        line_item = {
            "price_data": {
                "currency": "usd",
                "unit_amount": p["amount_cents"],
                "recurring": {"interval": p["interval"]},
                "product_data": {"name": f"NexusAI Talent OS — {p['name']}"},
            },
            "quantity": 1,
        }

    billing_state = ((tenant.settings or {}).get("billing") or {})
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[line_item],
            customer=billing_state.get("stripe_customer_id") or None,
            client_reference_id=org_id,
            metadata={"org_id": org_id, "plan": plan},
            subscription_data={"metadata": {"org_id": org_id, "plan": plan}},
            success_url=f"{settings.APP_BASE_URL}/admin/settings?billing=success",
            cancel_url=f"{settings.APP_BASE_URL}/pricing?billing=cancelled",
        )
    except Exception as exc:  # noqa: BLE001 — degrade, never 500
        logger.warning("stripe checkout failed for org %s: %s", org_id, exc)
        return {"ok": False, "reason": f"stripe error: {exc}"}

    return {"ok": True, "url": session.url, "session_id": session.id}


async def handle_webhook(db: AsyncSession, payload: bytes, sig_header: str) -> dict:
    """Verify a Stripe webhook signature and apply plan changes to the tenant.

    Handled events:
      checkout.session.completed      → activate plan from metadata
      customer.subscription.deleted   → downgrade to free
    Unknown events are acknowledged and ignored (Stripe retries on non-2xx).
    """
    stripe = _stripe()
    if stripe is None:
        return {"ok": False, "reason": "stripe_sdk_not_installed"}
    if not settings.STRIPE_WEBHOOK_SECRET:
        return {"ok": False, "reason": "webhook_secret_not_configured"}

    try:
        stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:  # noqa: BLE001 — bad signature / payload
        logger.warning("stripe webhook signature verification failed: %s", exc)
        return {"ok": False, "reason": "invalid_signature"}

    # Signature is verified above; read fields from the raw JSON so this
    # stays independent of the SDK's object model across versions.
    import json
    event = json.loads(payload)
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        org_id, plan = meta.get("org_id"), meta.get("plan")
        if not org_id or plan not in PLANS:
            return {"ok": True, "handled": False, "reason": "missing metadata"}
        tenant = await db.get(Tenant, org_id)
        if tenant is None:
            return {"ok": True, "handled": False, "reason": "unknown org"}
        tenant.plan = plan
        s = dict(tenant.settings or {})
        s["billing"] = {
            **(s.get("billing") or {}),
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("subscription"),
            "plan": plan,
        }
        tenant.settings = s
        await db.commit()
        logger.info("billing: org %s activated plan %s", org_id, plan)
        return {"ok": True, "handled": True, "plan": plan}

    if etype == "customer.subscription.deleted":
        meta = obj.get("metadata") or {}
        org_id = meta.get("org_id")
        if not org_id:
            return {"ok": True, "handled": False, "reason": "missing metadata"}
        tenant = await db.get(Tenant, org_id)
        if tenant is None:
            return {"ok": True, "handled": False, "reason": "unknown org"}
        tenant.plan = "free"
        s = dict(tenant.settings or {})
        billing = dict(s.get("billing") or {})
        billing.pop("stripe_subscription_id", None)
        billing["plan"] = "free"
        s["billing"] = billing
        tenant.settings = s
        await db.commit()
        logger.info("billing: org %s downgraded to free", org_id)
        return {"ok": True, "handled": True, "plan": "free"}

    return {"ok": True, "handled": False, "type": etype}


async def billing_status(db: AsyncSession, org_id: str) -> dict:
    """Current plan + configuration state for the admin billing UI."""
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        return {"plan": None, "available": billing_available()}
    billing = ((tenant.settings or {}).get("billing") or {})
    return {
        "plan": tenant.plan or "free",
        "available": billing_available(),
        "has_subscription": bool(billing.get("stripe_subscription_id")),
    }
