"""NexusAI Talent OS — White-label embeddable widget routes.

PUBLIC endpoints (no auth) — orchestrator must allowlist:
  GET /api/v1/widget/config/{org_id}
  GET /api/v1/widget/embed/{org_id}
  GET /api/v1/widget/loader.js

These are consumed cross-origin from customers' careers sites, so they carry
their own CORS headers driven by WIDGET_ALLOWED_ORIGINS (never credentialed —
independent of the app-wide credentialed CORS allowlist).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Tenant
from app.services import widget_service as widget

router = APIRouter()

CONFIG_CACHE = "public, max-age=300"
LOADER_CACHE = "public, max-age=3600"


def _guard():
    if not settings.FEATURE_WHITE_LABEL:
        raise HTTPException(403, "White-label feature disabled")


def _widget_cors(request: Request) -> dict[str, str]:
    """CORS for anonymous, non-credentialed widget requests on third-party sites."""
    allowed = settings.WIDGET_ALLOWED_ORIGINS
    if "*" in allowed:
        return {"Access-Control-Allow-Origin": "*"}
    origin = request.headers.get("origin", "")
    if origin and origin in allowed:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    return {"Vary": "Origin"}


async def _get_tenant_or_404(org_id: str, db: AsyncSession) -> Tenant:
    if not widget.ORG_ID_RE.match(org_id):
        raise HTTPException(404, "Unknown organization")
    tenant = await db.get(Tenant, org_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(404, "Unknown organization")
    return tenant


@router.get("/config/{org_id}")
async def get_config(
    org_id: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """PUBLIC — branding JSON for the embeddable widget."""
    _guard()
    tenant = await _get_tenant_or_404(org_id, db)
    response.headers.update(_widget_cors(request))
    response.headers["Cache-Control"] = CONFIG_CACHE
    return widget.widget_config(tenant)


@router.get("/embed/{org_id}")
async def get_embed(
    org_id: str,
    request: Request,
    response: Response,
    format: str = "json",
    db: AsyncSession = Depends(get_db),
):
    """PUBLIC — paste-able embed snippet (HTML or JSON)."""
    _guard()
    await _get_tenant_or_404(org_id, db)
    snippet = widget.embed_snippet(org_id, settings.API_BASE_URL)
    if format == "html":
        # Snippet is inert markup for copy/paste; serve as text so the API
        # origin never executes tenant-influenced HTML.
        return PlainTextResponse(
            snippet, media_type="text/plain; charset=utf-8", headers=_widget_cors(request)
        )
    response.headers.update(_widget_cors(request))
    return {"snippet": snippet}


@router.get("/loader.js")
async def get_loader(request: Request):
    """PUBLIC — small JS loader served as application/javascript."""
    _guard()
    js = widget.loader_js(settings.API_BASE_URL, settings.APP_BASE_URL)
    headers = {**_widget_cors(request), "Cache-Control": LOADER_CACHE}
    return PlainTextResponse(js, media_type="application/javascript", headers=headers)
