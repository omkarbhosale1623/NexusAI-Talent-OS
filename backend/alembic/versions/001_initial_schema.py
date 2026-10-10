"""Initial schema — NexusAI Talent OS (14 tables)"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("tenants",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("settings", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="admin"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_user_org_email", "users", ["org_id", "email"])

    op.create_table("auth_sessions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_auth_token", "auth_sessions", ["token_hash"])

    op.create_table("question_banks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("source", sa.String(50), server_default="upload"),
        sa.Column("role_tag", sa.String(100)),
        sa.Column("question_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_bank_org", "question_banks", ["org_id"])

    op.create_table("jobs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("location", sa.String(255)),
        sa.Column("employment_type", sa.String(50), server_default="full_time"),
        sa.Column("experience_min", sa.Integer, server_default="0"),
        sa.Column("experience_max", sa.Integer),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("salary_currency", sa.String(10), server_default="USD"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requirements", sa.Text),
        sa.Column("nice_to_have", sa.Text),
        sa.Column("required_skills", sa.JSON),
        sa.Column("nice_to_have_skills", sa.JSON),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("eligibility_threshold", sa.Float, server_default="0.6"),
        sa.Column("auto_shortlist", sa.Boolean, server_default="true"),
        sa.Column("rounds_config", sa.JSON),
        sa.Column("question_bank_id", sa.String, sa.ForeignKey("question_banks.id")),
        sa.Column("published_at", sa.DateTime),
        sa.Column("closed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_job_org_status", "jobs", ["org_id", "status"])

    op.create_table("questions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("bank_id", sa.String, sa.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("topic", sa.String(100)),
        sa.Column("competency", sa.String(100), server_default="general"),
        sa.Column("difficulty", sa.String(20), server_default="medium"),
        sa.Column("round_type", sa.String(50)),
        sa.Column("expected_answer", sa.Text),
        sa.Column("keywords", sa.JSON),
        sa.Column("follow_up_hints", sa.JSON),
        sa.Column("order_index", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_question_bank_round", "questions", ["bank_id", "round_type"])

    op.create_table("candidates",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("portfolio_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_candidate_org_email", "candidates", ["org_id", "email"])

    op.create_table("applications",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_id", sa.String, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("candidate_id", sa.String, sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="applied"),
        sa.Column("resume_s3_key", sa.String(1000)),
        sa.Column("resume_filename", sa.String(500)),
        sa.Column("cover_letter", sa.Text),
        sa.Column("years_experience", sa.Float),
        sa.Column("expected_salary", sa.Integer),
        sa.Column("expected_salary_currency", sa.String(10), server_default="USD"),
        sa.Column("parsed_resume", sa.JSON),
        sa.Column("eligibility_score", sa.Float),
        sa.Column("eligibility_breakdown", sa.JSON),
        sa.Column("screening_notes", sa.Text),
        sa.Column("applied_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("shortlisted_at", sa.DateTime),
        sa.Column("rejected_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_app_org_status", "applications", ["org_id", "status"])
    op.create_index("idx_app_job", "applications", ["job_id"])

    op.create_table("interview_slots",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_id", sa.String, sa.ForeignKey("jobs.id")),
        sa.Column("slot_datetime", sa.DateTime, nullable=False),
        sa.Column("duration_minutes", sa.Integer, server_default="60"),
        sa.Column("is_available", sa.Boolean, server_default="true"),
        sa.Column("max_bookings", sa.Integer, server_default="1"),
        sa.Column("current_bookings", sa.Integer, server_default="0"),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_slot_org_dt", "interview_slots", ["org_id", "slot_datetime"])

    op.create_table("interviews",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("application_id", sa.String, sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("job_id", sa.String, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("candidate_id", sa.String, sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("slot_id", sa.String, sa.ForeignKey("interview_slots.id")),
        sa.Column("question_bank_id", sa.String, sa.ForeignKey("question_banks.id")),
        sa.Column("token", sa.String(255), unique=True, nullable=False),
        sa.Column("schedule_token", sa.String(255), unique=True),
        sa.Column("status", sa.String(50), server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("evaluated_at", sa.DateTime),
        sa.Column("current_round", sa.String(50), server_default="intro"),
        sa.Column("current_question_index", sa.Integer, server_default="0"),
        sa.Column("question_order", sa.JSON),
        sa.Column("total_questions", sa.Integer, server_default="0"),
        sa.Column("livekit_room", sa.String(255)),
        sa.Column("proctoring_enabled", sa.Boolean, server_default="true"),
        sa.Column("proctoring_risk_score", sa.Float, server_default="0"),
        sa.Column("proctoring_events_count", sa.Integer, server_default="0"),
        sa.Column("invite_sent_at", sa.DateTime),
        sa.Column("reminder_1h_sent", sa.Boolean, server_default="false"),
        sa.Column("reminder_24h_sent", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_interview_token", "interviews", ["token"])
    op.create_index("idx_interview_org_status", "interviews", ["org_id", "status"])
    op.create_index("idx_interview_schedule_token", "interviews", ["schedule_token"])

    op.create_table("answers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("interview_id", sa.String, sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("question_id", sa.String, sa.ForeignKey("questions.id")),
        sa.Column("question_text", sa.Text),
        sa.Column("answer_text", sa.Text, nullable=False),
        sa.Column("round_type", sa.String(50), server_default="technical"),
        sa.Column("is_follow_up", sa.Boolean, server_default="false"),
        sa.Column("follow_up_to_id", sa.String, sa.ForeignKey("answers.id")),
        sa.Column("follow_up_count", sa.Integer, server_default="0"),
        sa.Column("audio_s3_key", sa.String(1000)),
        sa.Column("audio_duration_seconds", sa.Float),
        sa.Column("word_count", sa.Integer, server_default="0"),
        sa.Column("confidence_score", sa.Float),
        sa.Column("ml_signals", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_answer_interview", "answers", ["interview_id"])

    op.create_table("evaluations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("interview_id", sa.String, sa.ForeignKey("interviews.id"), unique=True, nullable=False),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("overall_rating", sa.String(20)),
        sa.Column("recommendation", sa.String(30)),
        sa.Column("executive_summary", sa.Text),
        sa.Column("hiring_notes", sa.Text),
        sa.Column("risk_flags", sa.JSON),
        sa.Column("communication", sa.JSON),
        sa.Column("competency_scores", sa.JSON),
        sa.Column("round_scores", sa.JSON),
        sa.Column("skill_gaps", sa.JSON),
        sa.Column("salary_recommendation", sa.JSON),
        sa.Column("llm_model_used", sa.String(100)),
        sa.Column("llm_tokens_used", sa.Integer, server_default="0"),
        sa.Column("generation_time_ms", sa.Integer),
        sa.Column("report_emailed_at", sa.DateTime),
        sa.Column("report_pdf_s3_key", sa.String(1000)),
        sa.Column("candidate_report_shared", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_eval_org", "evaluations", ["org_id"])

    op.create_table("answer_evaluations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("evaluation_id", sa.String, sa.ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answer_id", sa.String, sa.ForeignKey("answers.id"), nullable=False),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("relevance", sa.Float, server_default="0"),
        sa.Column("depth", sa.Float, server_default="0"),
        sa.Column("accuracy", sa.Float, server_default="0"),
        sa.Column("communication", sa.Float, server_default="0"),
        sa.Column("confidence", sa.Float, server_default="0"),
        sa.Column("total_score", sa.Float, server_default="0"),
        sa.Column("rating", sa.String(20)),
        sa.Column("candidate_feedback", sa.Text),
        sa.Column("detailed_analysis", sa.Text),
        sa.Column("strengths", sa.JSON),
        sa.Column("improvements", sa.JSON),
        sa.Column("keywords_detected", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("proctoring_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("interview_id", sa.String, sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_type", sa.String(50)),
        sa.Column("severity", sa.String(10), server_default="low"),
        sa.Column("confidence", sa.Float),
        sa.Column("metadata", sa.JSON),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_proctor_interview", "proctoring_events", ["interview_id"])

    op.create_table("audit_logs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String, sa.ForeignKey("tenants.id")),
        sa.Column("user_id", sa.String),
        sa.Column("action", sa.String(50)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("metadata", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_org_ts", "audit_logs", ["org_id", "created_at"])


def downgrade():
    for tbl in ["audit_logs", "proctoring_events", "answer_evaluations", "evaluations",
                "answers", "interviews", "interview_slots", "applications", "candidates",
                "questions", "jobs", "question_banks", "auth_sessions", "users", "tenants"]:
        op.drop_table(tbl)
