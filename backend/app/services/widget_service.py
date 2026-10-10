"""NexusAI Talent OS — White-label embeddable widget service.

Everything produced here is served to anonymous visitors and injected into
third-party pages, so every tenant-controlled value is validated/escaped:
  - org_id is HTML-escaped before landing in the embed snippet;
  - primary_color must be a hex color (else default) — it is concatenated
    into inline CSS on the host page;
  - logo_url must be http(s);
  - text fields are length-capped (rendered via textContent, so no HTML risk).
"""
from __future__ import annotations

import html
import re
from typing import Any, Optional

from app.core.config import settings

DEFAULT_PRIMARY = "#0A66C2"

ORG_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_MAX_TEXT = 200


def _safe_color(value: Any) -> str:
    return value if isinstance(value, str) and _HEX_COLOR_RE.match(value) else DEFAULT_PRIMARY


def _safe_url(value: Any) -> str:
    if isinstance(value, str) and value.lower().startswith(("https://", "http://")):
        return value[:2048]
    return ""


def _safe_text(value: Any, fallback: str = "") -> str:
    return value[:_MAX_TEXT] if isinstance(value, str) and value else fallback


def widget_config(tenant: Optional[Any]) -> dict:
    """Build white-label branding from tenant.settings.branding with sensible defaults."""
    s: dict = {}
    name = "NexusAI"
    if tenant is not None:
        s = getattr(tenant, "settings", None) or {}
        name = getattr(tenant, "name", None) or "NexusAI"
    branding = s.get("branding") if isinstance(s, dict) else None
    if not isinstance(branding, dict):
        branding = {}
    company = _safe_text(branding.get("company_name"), name)
    return {
        "logo_url": _safe_url(branding.get("logo_url")),
        "primary_color": _safe_color(branding.get("primary_color")),
        "company_name": company,
        "welcome_text": _safe_text(
            branding.get("welcome_text"), f"Explore careers at {company}"
        ),
    }


def embed_snippet(org_id: str, base_url: Optional[str] = None) -> str:
    """HTML snippet recruiters paste on their careers page."""
    api = base_url or settings.API_BASE_URL
    loader = f"{api}/api/v1/widget/loader.js"
    org = html.escape(org_id, quote=True)
    return (
        f'<!-- NexusAI Talent widget -->\n'
        f'<div id="nexusai-widget" data-org="{org}"></div>\n'
        f'<script src="{loader}" data-org="{org}" async></script>'
    )


def loader_js(api_base: Optional[str] = None, app_base: Optional[str] = None) -> str:
    """Minimal JS loader: fetches config, renders a branded button -> public job board."""
    api = api_base or settings.API_BASE_URL
    app = app_base or settings.APP_BASE_URL
    return (
        "(function(){\n"
        "  var s=document.currentScript||document.querySelector('script[src*=\"loader.js\"]');\n"
        "  var org=(s&&s.getAttribute('data-org'))||"
        "(document.getElementById('nexusai-widget')||{}).getAttribute&&"
        "document.getElementById('nexusai-widget').getAttribute('data-org');\n"
        f"  var API={api!r};var APP={app!r};\n"
        "  var mount=document.getElementById('nexusai-widget');\n"
        "  if(!mount||!org){return;}\n"
        "  function render(cfg){\n"
        "    cfg=cfg||{};\n"
        "    var color=/^#[0-9a-fA-F]{3,8}$/.test(cfg.primary_color||'')?cfg.primary_color:'#0A66C2';\n"
        "    var name=cfg.company_name||'Careers';\n"
        "    var board=APP+'/jobs?org='+encodeURIComponent(org);\n"
        "    var wrap=document.createElement('div');\n"
        "    wrap.style.cssText='font-family:system-ui,sans-serif;display:inline-block;';\n"
        "    if(cfg.logo_url&&/^https?:\\/\\//i.test(cfg.logo_url)){"
        "var img=document.createElement('img');img.src=cfg.logo_url;"
        "img.alt=name;img.style.cssText='max-height:32px;display:block;margin-bottom:8px;';"
        "wrap.appendChild(img);}\n"
        "    if(cfg.welcome_text){var p=document.createElement('p');"
        "p.textContent=cfg.welcome_text;p.style.cssText='margin:0 0 8px;font-size:14px;';"
        "wrap.appendChild(p);}\n"
        "    var a=document.createElement('a');a.href=board;a.target='_blank';"
        "a.rel='noopener';a.textContent='View Open Roles';\n"
        "    a.style.cssText='display:inline-block;padding:10px 18px;border-radius:6px;"
        "text-decoration:none;color:#fff;font-weight:600;background:'+color+';';\n"
        "    wrap.appendChild(a);mount.innerHTML='';mount.appendChild(wrap);\n"
        "  }\n"
        "  try{\n"
        "    fetch(API+'/api/v1/widget/config/'+encodeURIComponent(org))\n"
        "      .then(function(r){return r.json();}).then(render)\n"
        "      .catch(function(){render({});});\n"
        "  }catch(e){render({});}\n"
        "})();\n"
    )
