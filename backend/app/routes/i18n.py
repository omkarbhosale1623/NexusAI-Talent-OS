"""NexusAI Talent OS — i18n routes.

Mounted under ``/api/v1/i18n``. ``/locales`` and ``/bundle/{locale}`` are
PUBLIC (no org context required) so the candidate-facing UI can localize before
auth. ``/translate`` is also usable without org context (MVP).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.i18n_service import get_bundle, supported, translate_text

router = APIRouter()

# Candidate-facing LLM endpoint — bounded input so it can't be abused as a
# free-form LLM proxy (also rate-limited per-IP in RateLimitMiddleware).
MAX_TRANSLATE_CHARS = 4000


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TRANSLATE_CHARS)
    target_locale: str = Field(min_length=2, max_length=10)


@router.get("/locales")
async def locales():
    """PUBLIC — supported locales + default."""
    return {"locales": supported(), "default": settings.DEFAULT_LOCALE}


@router.get("/bundle/{locale}")
async def bundle(locale: str):
    """PUBLIC — translation bundle for a locale (falls back to en)."""
    return get_bundle(locale)


@router.post("/translate")
async def translate(body: TranslateIn):
    if not settings.FEATURE_I18N:
        raise HTTPException(404, "i18n is disabled")
    if body.target_locale.lower() not in [l.lower() for l in settings.SUPPORTED_LOCALES]:
        raise HTTPException(422, f"Unsupported locale: {body.target_locale}")
    return await translate_text(body.text, body.target_locale)
