"""Unit tests for the pure (no DB / no network) logic in the feature services."""
import asyncio
import warnings

warnings.filterwarnings("ignore")


# ── Prosody / emotion ───────────────────────────────────────────────────────
def test_prosody_text_confidence_ranges():
    from app.services.prosody_service import text_confidence
    strong = text_confidence(
        "I led the migration to a microservices architecture, reducing latency "
        "by forty percent through caching and connection pooling.", 12.0)
    weak = text_confidence("um, i think maybe, not sure, i guess", 8.0)
    assert 0.0 <= strong["confidence"] <= 1.0
    assert 0.0 <= weak["confidence"] <= 1.0
    assert strong["confidence"] > weak["confidence"]
    assert "emotion" in strong


def test_prosody_handles_empty():
    from app.services.prosody_service import text_confidence
    out = text_confidence("", None)
    assert 0.0 <= out["confidence"] <= 1.0


def test_analyze_prosody_async_text_only():
    from app.services.prosody_service import analyze_prosody
    out = asyncio.run(analyze_prosody(None, "I built a real-time pipeline.", 5.0))
    assert out["method"] in ("heuristic", "wav2vec2")
    assert 0.0 <= out["confidence"] <= 1.0


# ── Fraud detection ─────────────────────────────────────────────────────────
def test_fraud_weights_present():
    from app.services.fraud_service import FRAUD_EVENT_WEIGHTS
    for ev in ("tab_switch", "paste", "multiple_faces", "audio_anomaly"):
        assert ev in FRAUD_EVENT_WEIGHTS
        assert FRAUD_EVENT_WEIGHTS[ev] > 0


def test_detect_audio_anomaly():
    from app.services.fraud_service import detect_audio_anomaly
    base = {"pitch_variability": 0.2, "speech_rate_wpm": 130}
    spike = {"pitch_variability": 0.9, "speech_rate_wpm": 240}
    res = detect_audio_anomaly(spike, base)
    assert "anomaly" in res and "score" in res


# ── Benchmarks ──────────────────────────────────────────────────────────────
def test_benchmark_stats_helpers():
    from app.services import benchmark_service as b
    data = [10, 20, 30, 40, 50]
    assert b._mean(data) == 30
    assert b._median(data) == 30
    assert 0 <= b._percentile_rank(data, 30) <= 100
    assert b._percentile(data, 50) == 30


# ── i18n ────────────────────────────────────────────────────────────────────
def test_i18n_bundles_and_fallback():
    from app.services.i18n_service import t, get_bundle, supported
    assert "en" in supported()
    en = get_bundle("en")
    assert isinstance(en, dict)
    strings = en.get("strings", en)
    assert isinstance(strings, dict) and len(strings) >= 5
    # unknown locale falls back to en, never raises
    assert isinstance(get_bundle("xx"), dict)
    # t() returns a string for a known key in any locale
    assert isinstance(t(next(iter(strings)), "es"), str)


# ── Coding execution ────────────────────────────────────────────────────────
def test_coding_problem_bank():
    from app.services.code_exec_service import list_problems, get_problem
    probs = list_problems()
    assert len(probs) >= 3
    pid = probs[0]["id"]
    p = get_problem(pid)
    assert p and "starter_code" in p


# ── Panel personas ──────────────────────────────────────────────────────────
def test_panel_default_personas():
    from app.services.panel_service import DEFAULT_PERSONAS, resolve_personas
    assert len(DEFAULT_PERSONAS) >= 3

    class _Job:
        panel_personas = None
    assert resolve_personas(_Job()) == DEFAULT_PERSONAS


# ── White-label widget ──────────────────────────────────────────────────────
def test_widget_config_and_snippet():
    from app.services.widget_service import widget_config, embed_snippet

    class _T:
        id = "org-123"
        name = "Acme"
        settings = {}
    cfg = widget_config(_T())
    assert cfg.get("company_name") == "Acme"
    snip = embed_snippet("org-123", "http://localhost:8000")
    assert "org-123" in snip and "<script" in snip.lower()


# ── LiveKit / orchestration availability (no creds → graceful) ──────────────
def test_livekit_and_graph_availability_flags():
    from app.services.livekit_service import livekit_available
    from app.services.orchestrator_service import graph_available
    assert isinstance(livekit_available(), bool)
    assert isinstance(graph_available(), bool)
