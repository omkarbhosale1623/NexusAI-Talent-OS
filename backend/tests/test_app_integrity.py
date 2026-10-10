"""App-level integrity tests — import the app and assert every feature router
is registered. Runs without a database or network (lifespan is not started)."""
import warnings

warnings.filterwarnings("ignore")


def test_app_imports_and_registers_routers():
    from app.main import app
    paths = {r.path for r in app.routes}
    # Core
    assert "/health" in paths
    assert "/api/v1/auth/login" in paths
    # One representative path per new feature module
    expected = [
        "/api/v1/intelligence/{interview_id}/fraud-summary",
        "/api/v1/recordings/{interview_id}/playback",
        "/api/v1/coding/problems",
        "/api/v1/panel/{interview_id}/personas",
        "/api/v1/benchmarks/{interview_id}",
        "/api/v1/ats/connections",
        "/api/v1/calendar/connections",
        "/api/v1/messaging/sms",
        "/api/v1/widget/loader.js",
        "/api/v1/orchestration/status",
        "/api/v1/warehouse/status",
        "/api/v1/learning/stats",
        "/api/v1/bulk/upload",
        "/api/v1/i18n/locales",
        "/api/v1/livekit/status",
    ]
    missing = [p for p in expected if p not in paths]
    assert not missing, f"missing feature routes: {missing}"


def test_all_models_define_tablename():
    from app.models import models
    from app.models.models import Base
    # New tables present in metadata
    tables = set(Base.metadata.tables)
    for t in ("coding_submissions", "recruiter_feedback", "ats_connections",
              "calendar_connections", "outbound_messages"):
        assert t in tables, f"{t} not in metadata"
    # New columns on interviews/jobs
    iv_cols = set(models.Interview.__table__.columns.keys())
    for c in ("transport", "mode", "locale", "fraud_risk_score", "recording_s3_key"):
        assert c in iv_cols
    job_cols = set(models.Job.__table__.columns.keys())
    for c in ("interview_mode", "panel_personas", "coding_config"):
        assert c in job_cols
