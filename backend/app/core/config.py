"""NexusAI Talent OS — Settings"""
import secrets
from functools import lru_cache
from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    APP_NAME: str = "NexusAI Talent OS"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    API_BASE_URL: str = "http://localhost:8000"
    APP_BASE_URL: str = "http://localhost:3000"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/nexusai_talent"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 300
    DB_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    TTS_CACHE_TTL: int = 86400
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRE_HOURS: int = 72
    MAGIC_LINK_EXPIRE_HOURS: int = 48
    SCHEDULE_WINDOW_MINUTES: int = 30
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemini-2.5-flash"
    LLM_FALLBACK_MODELS: List[str] = ["meta-llama/llama-3.3-70b-instruct","meta-llama/llama-3.1-8b-instruct:free"]
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_FAST_MODEL: str = "google/gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2"
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_LANGUAGE: str = "en"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "nexusai-talent-os"
    S3_PRESIGNED_URL_EXPIRY: int = 3600
    R2_ENDPOINT_URL: str = ""
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "omkarbhosale1623@gmail.com"
    EMAIL_FROM_NAME: str = "NexusAI Talent OS"
    EMAIL_ENABLED: bool = True
    SENTRY_DSN: str = ""
    RATE_LIMIT_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_FOLLOW_UPS_PER_QUESTION: int = 2
    FOLLOW_UP_CONFIDENCE_THRESHOLD: float = 0.45
    FOLLOW_UP_MIN_WORD_COUNT: int = 30
    ELIGIBILITY_SKILLS_WEIGHT: float = 0.40
    ELIGIBILITY_EXPERIENCE_WEIGHT: float = 0.30
    ELIGIBILITY_EDUCATION_WEIGHT: float = 0.20
    ELIGIBILITY_BONUS_WEIGHT: float = 0.10
    ELIGIBILITY_AUTO_SHORTLIST_THRESHOLD: float = 0.80
    ELIGIBILITY_AUTO_REJECT_THRESHOLD: float = 0.30
    FACE_DETECTION_CONFIDENCE: float = 0.7
    MULTIPLE_FACES_THRESHOLD: int = 2
    PROCTORING_RISK_LOW_THRESHOLD: float = 0.3
    PROCTORING_RISK_MEDIUM_THRESHOLD: float = 0.6
    PROCTORING_RISK_HIGH_THRESHOLD: float = 0.8
    FEATURE_LIVEKIT: bool = False
    FEATURE_ML_PIPELINE: bool = False
    FEATURE_AI_QUESTION_GEN: bool = True
    FEATURE_FOLLOW_UP: bool = True
    FEATURE_PROCTORING: bool = True
    FEATURE_CANDIDATE_REPORT_VIEW: bool = True
    FEATURE_SALARY_RECOMMENDATION: bool = True
    DEFAULT_ORG_ID: str = "default"
    HUGGINGFACE_TOKEN: str = ""
    MAX_REDIS_CONNECTIONS: int = 20
    REDIS_MAX_CONNECTIONS: int = 20

    # ── Speech emotion / prosody scoring ───────────────────────────────────
    FEATURE_PROSODY: bool = True
    PROSODY_MODEL: str = "heuristic"  # heuristic | wav2vec2 (needs transformers+torch)

    # ── Advanced fraud detection ───────────────────────────────────────────
    FEATURE_FRAUD_DETECTION: bool = True
    FRAUD_TAB_SWITCH_WEIGHT: float = 0.08
    FRAUD_PASTE_WEIGHT: float = 0.12
    FRAUD_MULTI_FACE_WEIGHT: float = 0.20
    FRAUD_AUDIO_ANOMALY_WEIGHT: float = 0.10
    FRAUD_HIGH_RISK_THRESHOLD: float = 0.6

    # ── Video recording & playback ─────────────────────────────────────────
    FEATURE_VIDEO_RECORDING: bool = True
    VIDEO_MAX_SIZE_MB: int = 500
    VIDEO_RETENTION_DAYS: int = 90

    # ── Coding interview environment ───────────────────────────────────────
    FEATURE_CODING: bool = True
    CODE_EXEC_PROVIDER: str = "piston"  # piston | judge0 | none
    PISTON_URL: str = "https://emkc.org/api/v2/piston"
    JUDGE0_URL: str = ""
    JUDGE0_API_KEY: str = ""
    CODE_EXEC_TIMEOUT_S: int = 10

    # ── Panel interview mode ───────────────────────────────────────────────
    FEATURE_PANEL: bool = True

    # ── Benchmarks ─────────────────────────────────────────────────────────
    FEATURE_BENCHMARKS: bool = True

    # ── ATS integrations ───────────────────────────────────────────────────
    FEATURE_ATS: bool = True
    GREENHOUSE_BASE_URL: str = "https://harvest.greenhouse.io/v1"
    LEVER_BASE_URL: str = "https://api.lever.co/v1"
    WORKDAY_BASE_URL: str = ""

    # ── White-label / embeddable widget ────────────────────────────────────
    FEATURE_WHITE_LABEL: bool = True
    WIDGET_ALLOWED_ORIGINS: List[str] = ["*"]

    # ── i18n ───────────────────────────────────────────────────────────────
    FEATURE_I18N: bool = True
    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: List[str] = ["en", "es", "fr", "de", "hi", "pt", "ja", "zh", "ar"]

    # ── LangGraph orchestration ────────────────────────────────────────────
    FEATURE_LANGGRAPH: bool = False  # needs langgraph extra

    # ── BigQuery / warehouse ───────────────────────────────────────────────
    FEATURE_WAREHOUSE: bool = False
    BIGQUERY_PROJECT: str = ""
    BIGQUERY_DATASET: str = "nexusai_talent"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # ── Continuous learning ────────────────────────────────────────────────
    FEATURE_CONTINUOUS_LEARNING: bool = True

    # ── Bulk resume / batch processing ─────────────────────────────────────
    FEATURE_BULK_UPLOAD: bool = True
    BULK_MAX_FILES: int = 200
    BULK_MAX_FILE_MB: int = 10

    # ── Calendar integration ───────────────────────────────────────────────
    FEATURE_CALENDAR: bool = True
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/calendar/google/callback"
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = "common"
    MS_REDIRECT_URI: str = "http://localhost:8000/api/v1/calendar/outlook/callback"

    # ── Billing (Stripe) ───────────────────────────────────────────────────
    FEATURE_BILLING: bool = True
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # Optional pre-created Stripe Price ids; when empty, checkout uses inline
    # price_data from the plan catalog (amounts in cents).
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""

    # ── SMS (Twilio) ───────────────────────────────────────────────────────
    FEATURE_SMS: bool = True
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── Kafka / streaming ──────────────────────────────────────────────────
    FEATURE_KAFKA: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PREFIX: str = "nexusai"
    KAFKA_SCHEMA_VERSION: int = 1
    KAFKA_DLQ_TOPIC: str = "nexusai.deadletter"
    KAFKA_CONSUMER_MAX_RETRIES: int = 3

    # ── Enterprise hardening ───────────────────────────────────────────────
    ENCRYPTION_KEY: str = ""               # Fernet key; REQUIRED in production
    HTTP_TIMEOUT: float = 15.0             # outbound 3rd-party call timeout (s)
    HTTP_RETRIES: int = 2                  # retries on transient failures
    RATE_LIMIT_PER_TENANT: int = 600      # requests/min per org (0 = disabled)
    REQUIRE_HTTPS: bool = False            # enable HSTS + redirect in prod
    OTEL_ENABLED: bool = False             # OpenTelemetry tracing (needs extra)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    GDPR_RETENTION_DAYS: int = 365        # auto-purge candidate data after N days
    DATA_RESIDENCY_REGION: str = "us"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        return [o.strip() for o in v.split(",")] if isinstance(v, str) else v

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()


def validate_production_secrets(s: "Settings" = settings) -> list[str]:
    """Return a list of misconfigurations that are unacceptable in production.
    Called at startup; in production the app refuses to boot if non-empty."""
    problems: list[str] = []
    if not s.is_production:
        return problems
    if not s.JWT_SECRET or len(s.JWT_SECRET) < 32:
        problems.append("JWT_SECRET must be set to a strong (>=32 char) value")
    if "localhost" in s.DATABASE_URL or "user:pass" in s.DATABASE_URL:
        problems.append("DATABASE_URL still points at the dev default")
    if not s.ENCRYPTION_KEY:
        problems.append("ENCRYPTION_KEY must be set (field encryption at rest)")
    if "*" in s.CORS_ORIGINS:
        problems.append("CORS_ORIGINS must not be '*' in production")
    if s.DEBUG:
        problems.append("DEBUG must be False in production")
    return problems
