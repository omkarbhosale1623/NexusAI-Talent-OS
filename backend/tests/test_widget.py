"""White-label widget API — security & behavior tests.

Covers: org validation (XSS via embed), unknown/inactive tenant 404,
branding sanitization, widget CORS headers, cache headers, loader target,
and org-scoped public job board.
"""
from tests.conftest import signup, auth

JOB_BODY = {
    "title": "Backend Engineer",
    "description": "Build and operate the hiring platform backend services. " * 3,
}


# ── Service-level sanitization ───────────────────────────────────────────────

def test_widget_config_sanitizes_branding():
    from app.services.widget_service import widget_config, DEFAULT_PRIMARY

    class _T:
        id = "org-123"
        name = "Acme"
        settings = {"branding": {
            "primary_color": "red;position:fixed}</style><script>x</script>",
            "logo_url": "javascript:alert(1)",
            "company_name": "A" * 500,
        }}

    cfg = widget_config(_T())
    assert cfg["primary_color"] == DEFAULT_PRIMARY          # non-hex rejected
    assert cfg["logo_url"] == ""                            # non-http(s) rejected
    assert len(cfg["company_name"]) == 200                  # length-capped


def test_widget_config_accepts_valid_branding():
    from app.services.widget_service import widget_config

    class _T:
        id = "org-123"
        name = "Acme"
        settings = {"branding": {
            "primary_color": "#FF5733",
            "logo_url": "https://cdn.acme.com/logo.png",
            "welcome_text": "Join us",
        }}

    cfg = widget_config(_T())
    assert cfg["primary_color"] == "#FF5733"
    assert cfg["logo_url"] == "https://cdn.acme.com/logo.png"
    assert cfg["welcome_text"] == "Join us"
    assert cfg["company_name"] == "Acme"


def test_embed_snippet_escapes_org_id():
    from app.services.widget_service import embed_snippet

    snip = embed_snippet('"><script>alert(1)</script>', "http://localhost:8000")
    assert "<script>alert(1)</script>" not in snip
    assert "&lt;script&gt;" in snip


# ── Route-level ──────────────────────────────────────────────────────────────

async def test_widget_config_for_real_tenant(client):
    acc = await signup(client, company="Acme")
    r = await client.get(f"/api/v1/widget/config/{acc['org_id']}")
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["company_name"]
    assert cfg["primary_color"].startswith("#")
    # Non-credentialed widget CORS + caching
    assert r.headers.get("access-control-allow-origin") == "*"
    assert "max-age" in r.headers.get("cache-control", "")


async def test_widget_config_unknown_org_404(client):
    r = await client.get("/api/v1/widget/config/does-not-exist")
    assert r.status_code == 404


async def test_widget_embed_rejects_malicious_org(client):
    # Path traversal / XSS payloads never reach the HTML snippet: invalid
    # org ids 404 before rendering.
    r = await client.get(
        '/api/v1/widget/embed/x"><img src=x onerror=alert(1)>', params={"format": "html"}
    )
    assert r.status_code == 404


async def test_widget_embed_html_served_inert(client):
    acc = await signup(client, company="Acme")
    r = await client.get(f"/api/v1/widget/embed/{acc['org_id']}", params={"format": "html"})
    assert r.status_code == 200
    # Never text/html on the API origin — copy/paste snippet only.
    assert r.headers["content-type"].startswith("text/plain")
    assert acc["org_id"] in r.text and "loader.js" in r.text


async def test_widget_loader_js(client):
    r = await client.get("/api/v1/widget/loader.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert "max-age" in r.headers.get("cache-control", "")
    # Button must target the org-scoped public board, not a dead route.
    assert "/jobs?org=" in r.text
    assert "/careers/" not in r.text


async def test_public_job_board_is_org_scoped(client):
    a = await signup(client, company="OrgA")
    b = await signup(client, company="OrgB")
    for acc, title in ((a, "A Role"), (b, "B Role")):
        r = await client.post(
            "/api/v1/jobs", json={**JOB_BODY, "title": title}, headers=auth(acc["token"])
        )
        assert r.status_code == 201, r.text
        job_id = r.json()["id"]
        r = await client.post(f"/api/v1/jobs/{job_id}/publish", headers=auth(acc["token"]))
        assert r.status_code == 200, r.text

    # Unauthenticated + ?org= → only that org's published jobs (widget flow).
    r = await client.get("/api/v1/jobs", params={"org": a["org_id"]})
    assert r.status_code == 200
    titles = [j["title"] for j in r.json()["items"]]
    assert titles == ["A Role"]
