"""
app/core/metrics.py — Custom Prometheus metrics for business observability.
"""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry(auto_describe=True)

# ── Interview metrics ─────────────────────────────────────────────────────
INTERVIEWS_CREATED = Counter(
    "interviews_created_total",
    "Total interview sessions created",
    ["org_id"],
    registry=REGISTRY,
)
INTERVIEWS_COMPLETED = Counter(
    "interviews_completed_total",
    "Total interview sessions completed",
    ["org_id"],
    registry=REGISTRY,
)
INTERVIEWS_ACTIVE = Gauge(
    "interviews_active",
    "Currently active interview sessions",
    registry=REGISTRY,
)
INTERVIEW_DURATION = Histogram(
    "interview_duration_seconds",
    "Interview session duration",
    buckets=[60, 300, 600, 900, 1200, 1800, 3600],
    registry=REGISTRY,
)

# ── LLM metrics ───────────────────────────────────────────────────────────
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API calls",
    ["model", "operation"],
    registry=REGISTRY,
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["model"],
    registry=REGISTRY,
)
LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM API call latency",
    ["model"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
    registry=REGISTRY,
)
LLM_ERRORS = Counter(
    "llm_errors_total",
    "Total LLM API failures",
    ["model", "error_type"],
    registry=REGISTRY,
)

# ── TTS / STT metrics ─────────────────────────────────────────────────────
TTS_REQUESTS = Counter(
    "tts_requests_total",
    "Total TTS synthesis calls",
    ["provider"],
    registry=REGISTRY,
)
TTS_CACHE_HITS = Counter(
    "tts_cache_hits_total",
    "TTS Redis cache hits",
    registry=REGISTRY,
)
TTS_CACHE_MISSES = Counter(
    "tts_cache_misses_total",
    "TTS Redis cache misses",
    registry=REGISTRY,
)
STT_REQUESTS = Counter(
    "stt_requests_total",
    "Total STT transcription calls",
    registry=REGISTRY,
)
STT_LATENCY = Histogram(
    "stt_duration_seconds",
    "STT transcription latency",
    buckets=[0.5, 1, 2, 5, 10, 20],
    registry=REGISTRY,
)

# ── Auth / security metrics ───────────────────────────────────────────────
AUTH_ATTEMPTS = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["result"],  # success | failure
    registry=REGISTRY,
)
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total rate limit rejections",
    ["path"],
    registry=REGISTRY,
)

# ── Evaluation metrics ────────────────────────────────────────────────────
EVALUATIONS_TRIGGERED = Counter(
    "evaluations_triggered_total",
    "Total evaluation jobs triggered",
    registry=REGISTRY,
)
EVALUATION_LATENCY = Histogram(
    "evaluation_duration_seconds",
    "Full evaluation pipeline latency",
    buckets=[5, 10, 20, 30, 60, 120],
    registry=REGISTRY,
)
EVALUATION_SCORES = Histogram(
    "evaluation_score",
    "Distribution of evaluation overall scores",
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    registry=REGISTRY,
)
