"""NexusAI Talent OS — Billing routes (Stripe plans & pricing).

Mounted under ``/api/v1/billing``.
  GET  /plans    — PUBLIC (pricing page catalog; middleware allowlists it)
  GET  /status   — staff: current org plan
  POST /checkout — admin: create a Stripe Checkout session
  POST /webhook  — PUBLIC (Stripe server-to-server; signature-verified)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import require_admin, require_staff
from app.core.config import settings
from app.core.database import get_db
from app.services import billing_service

router = APIRouter()


class CheckoutBody(BaseModel):
    plan: str = Field(min_length=1, max_length=32)


def _require_feature() -> None:
    if not settings.FEATURE_BILLING:
        raise HTTPException(403, "Billing is disabled")


@router.get("/plans")
async def get_plans():
    """PUBLIC — plan catalog for the pricing page (no secrets)."""
    _require_feature()
    return {"plans": billing_service.plan_catalog(),
            "available": billing_service.billing_available()}


@router.get("/status", dependencies=[Depends(require_staff)])
async def get_status(request: Request, db: AsyncSession = Depends(get_db)):
    _require_feature()
    return await billing_service.billing_status(db, request.state.org_id)


@router.post("/checkout", dependencies=[Depends(require_admin)])
async def create_checkout(body: CheckoutBody, request: Request,
                          db: AsyncSession = Depends(get_db)):
    """Admin-only: start a Stripe Checkout session for the caller's org."""
    _require_feature()
    result = await billing_service.create_checkout_session(
        db, request.state.org_id, body.plan)
    if not result.get("ok") and result.get("reason", "").startswith("unknown plan"):
        raise HTTPException(422, result["reason"])
    return result


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """PUBLIC — Stripe event delivery. Signature is the authentication."""
    _require_feature()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    result = await billing_service.handle_webhook(db, payload, sig)
    if not result.get("ok"):
        # 400 → Stripe will retry; nothing sensitive in the reason
        raise HTTPException(400, result.get("reason", "webhook rejected"))
    return result
