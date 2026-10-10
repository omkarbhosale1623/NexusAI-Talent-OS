"""Feature-module hardening tests — fraud, coding, recordings, i18n,
livekit, learning, bulk, eligibility threshold.

Each test targets a specific control added during enterprise hardening:
input allowlists/caps, tenant derivation, RBAC gates, and state guards.
"""
import secrets

from tests.conftest import signup, make_user, auth

RESUME_OK = {"title": "Backend Engineer",
             "description": "Build and operate the hiring platform backend services. " * 3}


async def make_interview(org_id: str, status: str = "active") -> dict:
    """Insert job → candidate → application → interview directly; return ids."""
    from app.core.database import AsyncSessionLocal
    from app.models.models import Application, Candidate, Interview, Job

    async with AsyncSessionLocal() as db:
        job = Job(org_id=org_id, title="Role", description="d" * 60)
        cand = Candidate(org_id=org_id, full_name="Cand",
                         email=f"c-{secrets.token_hex(4)}@x.io")
        db.add_all([job, cand])
        await db.flush()
        app_row = Application(org_id=org_id, job_id=job.id, candidate_id=cand.id)
        db.add(app_row)
        await db.flush()
        iv = Interview(org_id=org_id, application_id=app_row.id, job_id=job.id,
                       candidate_id=cand.id, token=secrets.token_urlsafe(24),
                       status=status)
        db.add(iv)
        await db.commit()
        return {"id": iv.id, "token": iv.token, "org_id": org_id}


# ── Fraud events (candidate-facing, public) ─────────────────────────────────

async def test_fraud_event_rejects_unknown_type(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.post(f"/api/v1/intelligence/{iv['id']}/fraud-event",
                          json={"event_type": "totally_made_up"})
    assert r.status_code == 422


async def test_fraud_event_confidence_clamped(client):
    """Negative confidence must never REDUCE the fraud score."""
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r1 = await client.post(f"/api/v1/intelligence/{iv['id']}/fraud-event",
                           json={"event_type": "paste"})
    assert r1.status_code == 200
    score_after_paste = r1.json()["fraud_risk_score"]
    r2 = await client.post(
        f"/api/v1/intelligence/{iv['id']}/fraud-event",
        json={"event_type": "tab_switch", "metadata": {"confidence": -1000}})
    assert r2.status_code == 200
    assert r2.json()["fraud_risk_score"] >= score_after_paste


async def test_fraud_event_blocked_after_completion(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"], status="completed")
    r = await client.post(f"/api/v1/intelligence/{iv['id']}/fraud-event",
                          json={"event_type": "paste"})
    assert r.status_code == 422


# ── Coding (candidate-facing exec) ──────────────────────────────────────────

async def test_coding_run_requires_real_interview(client):
    r = await client.post("/api/v1/coding/nonexistent-iv/run",
                          json={"language": "python", "source": "print(1)"})
    assert r.status_code == 404


async def test_coding_run_rejects_unknown_language(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.post(f"/api/v1/coding/{iv['id']}/run",
                          json={"language": "brainfuck", "source": "+"})
    assert r.status_code == 422


async def test_coding_submission_inherits_interview_org(client):
    """Submissions must carry the interview's org — not a global default."""
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.post(f"/api/v1/coding/{iv['id']}/run",
                          json={"language": "python", "source": "print(1)"})
    assert r.status_code == 200
    from app.core.database import AsyncSessionLocal
    from app.models.models import CodingSubmission
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        sub = await db.scalar(select(CodingSubmission).where(
            CodingSubmission.interview_id == iv["id"]))
        assert sub is not None and sub.org_id == acc["org_id"]


async def test_coding_submit_hides_expected_outputs(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.post(f"/api/v1/coding/{iv['id']}/submit",
                          json={"language": "python", "source": "print(1)",
                                "problem_id": "fizzbuzz"})
    assert r.status_code == 200
    for case in r.json()["cases"]:
        assert "expected" not in case and "got" not in case


async def test_coding_blocked_after_completion(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"], status="completed")
    r = await client.post(f"/api/v1/coding/{iv['id']}/run",
                          json={"language": "python", "source": "print(1)"})
    assert r.status_code == 409


# ── Recordings ──────────────────────────────────────────────────────────────

async def test_recording_upload_rejects_bad_content_type(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.post(
        f"/api/v1/recordings/{iv['id']}/upload",
        files={"file": ("evil.html", b"<script>", "text/html")})
    assert r.status_code == 415


async def test_recording_upload_no_silent_overwrite(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    from app.core.database import AsyncSessionLocal
    from app.models.models import Interview
    async with AsyncSessionLocal() as db:
        row = await db.get(Interview, iv["id"])
        row.recording_s3_key = "recordings/x/y.webm"
        await db.commit()
    r = await client.post(
        f"/api/v1/recordings/{iv['id']}/upload",
        files={"file": ("a.webm", b"\x1aE\xdf\xa3", "video/webm")})
    assert r.status_code == 409


async def test_recording_delete_requires_admin(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    recruiter_token = await make_user(acc["org_id"], "recruiter")
    r = await client.delete(f"/api/v1/recordings/{iv['id']}",
                            headers=auth(recruiter_token))
    assert r.status_code == 403
    r = await client.delete(f"/api/v1/recordings/{iv['id']}",
                            headers=auth(acc["token"]))
    assert r.status_code == 200


async def test_recording_playback_requires_auth(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    r = await client.get(f"/api/v1/recordings/{iv['id']}/playback")
    assert r.status_code == 401


# ── i18n (public LLM endpoint) ──────────────────────────────────────────────

async def test_translate_caps_text_and_locale(client):
    r = await client.post("/api/v1/i18n/translate",
                          json={"text": "x" * 5000, "target_locale": "es"})
    assert r.status_code == 422
    r = await client.post("/api/v1/i18n/translate",
                          json={"text": "hello", "target_locale": "xx"})
    assert r.status_code == 422


# ── LiveKit token minting ───────────────────────────────────────────────────

async def test_livekit_token_requires_entitlement(client):
    acc = await signup(client)
    iv = await make_interview(acc["org_id"])
    # anonymous, no interview token → refused
    r = await client.post(f"/api/v1/livekit/{iv['id']}/token",
                          json={"identity": "eve"})
    assert r.status_code == 403
    # wrong interview token → refused
    r = await client.post(f"/api/v1/livekit/{iv['id']}/token",
                          json={"identity": "eve", "interview_token": "guess"})
    assert r.status_code == 403
    # candidate's real interview token → passes the gate (feature may be off,
    # which returns ok=False gracefully, but never 401/403)
    r = await client.post(
        f"/api/v1/livekit/{iv['id']}/token",
        json={"identity": "cand", "interview_token": iv["token"]})
    assert r.status_code == 200


# ── Learning feedback ───────────────────────────────────────────────────────

async def test_feedback_rejects_foreign_interview(client):
    a = await signup(client, company="OrgA")
    b = await signup(client, company="OrgB")
    iv_b = await make_interview(b["org_id"])
    r = await client.post("/api/v1/learning/feedback",
                          json={"interview_id": iv_b["id"],
                                "recruiter_decision": "hire"},
                          headers=auth(a["token"]))
    assert r.status_code == 404


# ── Bulk upload per-file cap ────────────────────────────────────────────────

async def test_bulk_upload_skips_oversize_file(client):
    from app.core.config import settings
    acc = await signup(client)
    # create a job to attach to
    r = await client.post("/api/v1/jobs", json=RESUME_OK, headers=auth(acc["token"]))
    job_id = r.json()["id"]
    old = settings.BULK_MAX_FILE_MB
    settings.BULK_MAX_FILE_MB = 1
    try:
        big = b"x" * (1024 * 1024 + 100)
        r = await client.post(
            "/api/v1/bulk/upload",
            data={"job_id": job_id},
            files={"files": ("big.pdf", big, "application/pdf")},
            headers=auth(acc["token"]))
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] >= 1
        assert any("exceeds" in (res.get("error") or "") for res in body["results"])
    finally:
        settings.BULK_MAX_FILE_MB = old


# ── Eligibility threshold (user-requested: shortlist at >= 0.80) ────────────

def test_shortlist_threshold_is_80():
    from app.core.config import settings
    assert settings.ELIGIBILITY_AUTO_SHORTLIST_THRESHOLD == 0.80
