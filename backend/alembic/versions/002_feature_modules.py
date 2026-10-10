"""Feature-module schema — NexusAI Talent OS

Feature modules (coding, recruiter feedback, ATS, calendar, outbound msgs) plus
the columns added to `jobs` and `interviews` for panel/coding/i18n mode, fraud
scoring, and video recordings.

Idempotent: every table/column is created only when absent, so this is safe to
run against a fresh DB (after 001) OR over a database that already carries the
base 15 tables from an older dump (e.g. nexusai_talent.sql). In the latter case,
`alembic stamp 001_initial` first so Alembic doesn't try to recreate the base
tables, then `alembic upgrade head` applies just this revision.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "002_feature_modules"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def _insp():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _insp().get_table_names()


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(
        c["name"] == column for c in _insp().get_columns(table)
    )


def _add_column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def upgrade():
    # ── New columns on jobs ────────────────────────────────────────────────
    _add_column("jobs", sa.Column("interview_mode", sa.String(20), server_default="voice"))
    _add_column("jobs", sa.Column("panel_personas", sa.JSON))
    _add_column("jobs", sa.Column("coding_config", sa.JSON))
    _add_column("jobs", sa.Column("locale", sa.String(10), server_default="en"))

    # ── New columns on interviews ──────────────────────────────────────────
    _add_column("interviews", sa.Column("transport", sa.String(20), server_default="http"))
    _add_column("interviews", sa.Column("mode", sa.String(20), server_default="voice"))
    _add_column("interviews", sa.Column("locale", sa.String(10), server_default="en"))
    _add_column("interviews", sa.Column("fraud_risk_score", sa.Float, server_default="0"))
    _add_column("interviews", sa.Column("fraud_flags", sa.JSON))
    _add_column("interviews", sa.Column("recording_s3_key", sa.String(1000)))
    _add_column("interviews", sa.Column("recording_duration_seconds", sa.Float))

    # ── coding_submissions ─────────────────────────────────────────────────
    if not _has_table("coding_submissions"):
        op.create_table("coding_submissions",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("interview_id", sa.String, sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
            sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("problem_id", sa.String),
            sa.Column("problem_title", sa.String(255)),
            sa.Column("language", sa.String(40), server_default="python"),
            sa.Column("source_code", sa.Text, server_default=""),
            sa.Column("stdin", sa.Text),
            sa.Column("stdout", sa.Text),
            sa.Column("stderr", sa.Text),
            sa.Column("exit_code", sa.Integer),
            sa.Column("runtime_ms", sa.Integer),
            sa.Column("tests_passed", sa.Integer, server_default="0"),
            sa.Column("tests_total", sa.Integer, server_default="0"),
            sa.Column("status", sa.String(30), server_default="draft"),
            sa.Column("score", sa.Float),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("idx_coding_interview", "coding_submissions", ["interview_id"])

    # ── recruiter_feedback ─────────────────────────────────────────────────
    if not _has_table("recruiter_feedback"):
        op.create_table("recruiter_feedback",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("interview_id", sa.String, sa.ForeignKey("interviews.id")),
            sa.Column("evaluation_id", sa.String, sa.ForeignKey("evaluations.id")),
            sa.Column("user_id", sa.String),
            sa.Column("ai_recommendation", sa.String(30)),
            sa.Column("ai_score", sa.Float),
            sa.Column("recruiter_decision", sa.String(30)),
            sa.Column("recruiter_score", sa.Float),
            sa.Column("agreed_with_ai", sa.Boolean),
            sa.Column("rating", sa.Integer),
            sa.Column("notes", sa.Text),
            sa.Column("dimension_corrections", sa.JSON),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("idx_feedback_org", "recruiter_feedback", ["org_id"])

    # ── ats_connections ────────────────────────────────────────────────────
    if not _has_table("ats_connections"):
        op.create_table("ats_connections",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("provider", sa.String(40)),
            sa.Column("api_key", sa.String(500)),
            sa.Column("base_url", sa.String(500)),
            sa.Column("config", sa.JSON),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("last_sync_at", sa.DateTime),
            sa.Column("last_sync_status", sa.String(40)),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("idx_ats_org_provider", "ats_connections", ["org_id", "provider"])

    # ── calendar_connections ───────────────────────────────────────────────
    if not _has_table("calendar_connections"):
        op.create_table("calendar_connections",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("user_id", sa.String),
            sa.Column("provider", sa.String(20)),
            sa.Column("access_token", sa.Text),
            sa.Column("refresh_token", sa.Text),
            sa.Column("token_expires_at", sa.DateTime),
            sa.Column("calendar_id", sa.String(255)),
            sa.Column("email", sa.String(320)),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("idx_cal_org_provider", "calendar_connections", ["org_id", "provider"])

    # ── outbound_messages ──────────────────────────────────────────────────
    if not _has_table("outbound_messages"):
        op.create_table("outbound_messages",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("channel", sa.String(20)),
            sa.Column("to_address", sa.String(320)),
            sa.Column("template", sa.String(80)),
            sa.Column("body", sa.Text),
            sa.Column("provider_id", sa.String(255)),
            sa.Column("status", sa.String(30), server_default="queued"),
            sa.Column("error", sa.Text),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("idx_msg_org_channel", "outbound_messages", ["org_id", "channel"])


def downgrade():
    for tbl in ("outbound_messages", "calendar_connections", "ats_connections",
                "recruiter_feedback", "coding_submissions"):
        if _has_table(tbl):
            op.drop_table(tbl)
    for col in ("recording_duration_seconds", "recording_s3_key", "fraud_flags",
                "fraud_risk_score", "locale", "mode", "transport"):
        if _has_column("interviews", col):
            op.drop_column("interviews", col)
    for col in ("locale", "coding_config", "panel_personas", "interview_mode"):
        if _has_column("jobs", col):
            op.drop_column("jobs", col)
