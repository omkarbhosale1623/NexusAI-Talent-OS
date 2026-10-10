"""NexusAI Talent OS — SQLAlchemy Models (Complete)"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def new_uuid() -> str:
    return str(uuid.uuid4())

class Base(DeclarativeBase):
    pass

# ── Tenants ───────────────────────────────────────────────────────────────
class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# ── Users ─────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin")  # admin|recruiter
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_user_org_email", "org_id", "email"),)

# ── Auth Sessions ─────────────────────────────────────────────────────────
class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_auth_token", "token_hash"),)

# ── Jobs ──────────────────────────────────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time")
    # full_time|part_time|contract|internship
    experience_min: Mapped[int] = mapped_column(Integer, default=0)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    nice_to_have: Mapped[Optional[str]] = mapped_column(Text)
    required_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    nice_to_have_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    # draft|published|paused|closed|archived
    eligibility_threshold: Mapped[float] = mapped_column(Float, default=0.60)
    auto_shortlist: Mapped[bool] = mapped_column(Boolean, default=True)
    interview_mode: Mapped[str] = mapped_column(String(20), default="voice")  # voice|panel|coding
    panel_personas: Mapped[Optional[List[dict]]] = mapped_column(JSON)  # [{name,role,persona,voice}]
    coding_config: Mapped[Optional[dict]] = mapped_column(JSON)  # {language,problems:[...]}
    locale: Mapped[str] = mapped_column(String(10), default="en")
    rounds_config: Mapped[Optional[dict]] = mapped_column(JSON)
    # {intro:{enabled,duration,questions},technical:{...},behavioral:{...},hr:{...}}
    question_bank_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("question_banks.id"))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    applications: Mapped[List["Application"]] = relationship(back_populates="job")
    __table_args__ = (
        Index("idx_job_org_status", "org_id", "status"),
    )

# ── Candidates ────────────────────────────────────────────────────────────
class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    applications: Mapped[List["Application"]] = relationship(back_populates="candidate")
    __table_args__ = (Index("idx_candidate_org_email", "org_id", "email"),)

# ── Applications ──────────────────────────────────────────────────────────
class Application(Base):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey("candidates.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="applied")
    # applied|screening|shortlisted|rejected|interview_scheduled
    # interview_completed|evaluated|hired|offer_sent|offer_accepted|withdrawn
    resume_s3_key: Mapped[Optional[str]] = mapped_column(String(1000))
    resume_filename: Mapped[Optional[str]] = mapped_column(String(500))
    cover_letter: Mapped[Optional[str]] = mapped_column(Text)
    years_experience: Mapped[Optional[float]] = mapped_column(Float)
    expected_salary: Mapped[Optional[int]] = mapped_column(Integer)
    expected_salary_currency: Mapped[str] = mapped_column(String(10), default="USD")
    parsed_resume: Mapped[Optional[dict]] = mapped_column(JSON)
    eligibility_score: Mapped[Optional[float]] = mapped_column(Float)
    eligibility_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    # {skills_score, experience_score, education_score, bonus_score}
    screening_notes: Mapped[Optional[str]] = mapped_column(Text)
    applied_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    shortlisted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    interviews: Mapped[List["Interview"]] = relationship(back_populates="application")
    __table_args__ = (
        Index("idx_app_org_status", "org_id", "status"),
        Index("idx_app_job", "job_id"),
    )

# ── Question Banks ─────────────────────────────────────────────────────────
class QuestionBank(Base):
    __tablename__ = "question_banks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="upload")
    role_tag: Mapped[Optional[str]] = mapped_column(String(100))
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    questions: Mapped[List["Question"]] = relationship(back_populates="bank", cascade="all, delete-orphan")
    __table_args__ = (Index("idx_bank_org", "org_id"),)

# ── Questions ─────────────────────────────────────────────────────────────
class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    bank_id: Mapped[str] = mapped_column(String, ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(100))
    competency: Mapped[str] = mapped_column(String(100), default="general")
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    round_type: Mapped[Optional[str]] = mapped_column(String(50))
    # intro|technical|behavioral|hr
    expected_answer: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON)
    follow_up_hints: Mapped[Optional[List[str]]] = mapped_column(JSON)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    bank: Mapped["QuestionBank"] = relationship(back_populates="questions")
    __table_args__ = (Index("idx_question_bank_round", "bank_id", "round_type"),)

# ── Interview Slots (Admin-defined availability) ───────────────────────────
class InterviewSlot(Base):
    __tablename__ = "interview_slots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"))
    slot_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_bookings: Mapped[int] = mapped_column(Integer, default=1)
    current_bookings: Mapped[int] = mapped_column(Integer, default=0)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_slot_org_dt", "org_id", "slot_datetime"),)

# ── Interviews ────────────────────────────────────────────────────────────
class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey("candidates.id"), nullable=False)
    slot_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("interview_slots.id"))
    question_bank_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("question_banks.id"))
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    schedule_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    # scheduled|ready|active|completed|evaluated|cancelled|no_show
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    current_round: Mapped[str] = mapped_column(String(50), default="intro")
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    question_order: Mapped[Optional[List[str]]] = mapped_column(JSON)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    livekit_room: Mapped[Optional[str]] = mapped_column(String(255))
    transport: Mapped[str] = mapped_column(String(20), default="http")  # http|livekit
    mode: Mapped[str] = mapped_column(String(20), default="voice")  # voice|panel|coding
    locale: Mapped[str] = mapped_column(String(10), default="en")
    proctoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    proctoring_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    proctoring_events_count: Mapped[int] = mapped_column(Integer, default=0)
    fraud_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    fraud_flags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    recording_s3_key: Mapped[Optional[str]] = mapped_column(String(1000))
    recording_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    invite_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reminder_1h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    application: Mapped["Application"] = relationship(back_populates="interviews")
    answers: Mapped[List["Answer"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    evaluation: Mapped[Optional["Evaluation"]] = relationship(back_populates="interview", uselist=False)
    proctoring_events: Mapped[List["ProctoringEvent"]] = relationship(back_populates="interview")
    __table_args__ = (
        Index("idx_interview_token", "token"),
        Index("idx_interview_org_status", "org_id", "status"),
        Index("idx_interview_schedule_token", "schedule_token"),
    )

# ── Answers ───────────────────────────────────────────────────────────────
class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    question_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("questions.id"))
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    round_type: Mapped[str] = mapped_column(String(50), default="technical")
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_to_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("answers.id"))
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    audio_s3_key: Mapped[Optional[str]] = mapped_column(String(1000))
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    ml_signals: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    interview: Mapped["Interview"] = relationship(back_populates="answers")
    answer_evaluation: Mapped[Optional["AnswerEvaluation"]] = relationship(back_populates="answer", uselist=False)
    __table_args__ = (Index("idx_answer_interview", "interview_id"),)

# ── Evaluations ────────────────────────────────────────────────────────────
class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"), unique=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_rating: Mapped[str] = mapped_column(String(20))
    recommendation: Mapped[str] = mapped_column(String(30))
    # Strong Hire | Hire | Maybe | No Hire
    executive_summary: Mapped[Optional[str]] = mapped_column(Text)
    hiring_notes: Mapped[Optional[str]] = mapped_column(Text)
    risk_flags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    communication: Mapped[Optional[dict]] = mapped_column(JSON)
    competency_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    # {technical, communication, problem_solving, leadership, culture_fit}
    round_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    # {intro, technical, behavioral, hr}
    skill_gaps: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    salary_recommendation: Mapped[Optional[dict]] = mapped_column(JSON)
    # {min, max, currency, justification}
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100))
    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    report_emailed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    report_pdf_s3_key: Mapped[Optional[str]] = mapped_column(String(1000))
    candidate_report_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    interview: Mapped["Interview"] = relationship(back_populates="evaluation")
    answer_evaluations: Mapped[List["AnswerEvaluation"]] = relationship(back_populates="evaluation")
    __table_args__ = (Index("idx_eval_org", "org_id"),)

# ── Answer Evaluations ─────────────────────────────────────────────────────
class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    evaluation_id: Mapped[str] = mapped_column(String, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    answer_id: Mapped[str] = mapped_column(String, ForeignKey("answers.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=0)      # 0-10
    depth: Mapped[float] = mapped_column(Float, default=0)           # 0-10
    accuracy: Mapped[float] = mapped_column(Float, default=0)        # 0-10
    communication: Mapped[float] = mapped_column(Float, default=0)   # 0-10
    confidence: Mapped[float] = mapped_column(Float, default=0)      # 0-10
    total_score: Mapped[float] = mapped_column(Float, default=0)     # 0-100
    rating: Mapped[str] = mapped_column(String(20))
    candidate_feedback: Mapped[Optional[str]] = mapped_column(Text)
    detailed_analysis: Mapped[Optional[str]] = mapped_column(Text)
    strengths: Mapped[Optional[List[str]]] = mapped_column(JSON)
    improvements: Mapped[Optional[List[str]]] = mapped_column(JSON)
    keywords_detected: Mapped[Optional[List[str]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    evaluation: Mapped["Evaluation"] = relationship(back_populates="answer_evaluations")
    answer: Mapped["Answer"] = relationship(back_populates="answer_evaluation")

# ── Proctoring Events ──────────────────────────────────────────────────────
class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(10), default="low")
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    interview: Mapped["Interview"] = relationship(back_populates="proctoring_events")
    __table_args__ = (Index("idx_proctor_interview", "interview_id"),)

# ── Coding Submissions (live coding interview) ─────────────────────────────
class CodingSubmission(Base):
    __tablename__ = "coding_submissions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    problem_id: Mapped[Optional[str]] = mapped_column(String)
    problem_title: Mapped[Optional[str]] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(40), default="python")
    source_code: Mapped[str] = mapped_column(Text, default="")
    stdin: Mapped[Optional[str]] = mapped_column(Text)
    stdout: Mapped[Optional[str]] = mapped_column(Text)
    stderr: Mapped[Optional[str]] = mapped_column(Text)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer)
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tests_passed: Mapped[int] = mapped_column(Integer, default=0)
    tests_total: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft|ran|submitted
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_coding_interview", "interview_id"),)

# ── Recruiter Feedback (continuous learning signal) ────────────────────────
class RecruiterFeedback(Base):
    __tablename__ = "recruiter_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    interview_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("interviews.id"))
    evaluation_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("evaluations.id"))
    user_id: Mapped[Optional[str]] = mapped_column(String)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(String(30))
    ai_score: Mapped[Optional[float]] = mapped_column(Float)
    recruiter_decision: Mapped[str] = mapped_column(String(30))  # hire|no_hire|maybe
    recruiter_score: Mapped[Optional[float]] = mapped_column(Float)
    agreed_with_ai: Mapped[Optional[bool]] = mapped_column(Boolean)
    rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 quality of AI eval
    notes: Mapped[Optional[str]] = mapped_column(Text)
    dimension_corrections: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_feedback_org", "org_id"),)

# ── ATS Connections ────────────────────────────────────────────────────────
class ATSConnection(Base):
    __tablename__ = "ats_connections"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40))  # greenhouse|lever|workday
    api_key: Mapped[Optional[str]] = mapped_column(String(500))  # encrypted-at-rest in prod
    base_url: Mapped[Optional[str]] = mapped_column(String(500))
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_ats_org_provider", "org_id", "provider"),)

# ── Calendar Connections (Google / Outlook OAuth) ──────────────────────────
class CalendarConnection(Base):
    __tablename__ = "calendar_connections"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String(20))  # google|outlook
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_cal_org_provider", "org_id", "provider"),)

# ── Outbound Messages (SMS / email delivery log) ───────────────────────────
class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20))  # sms|email
    to_address: Mapped[str] = mapped_column(String(320))
    template: Mapped[Optional[str]] = mapped_column(String(80))
    body: Mapped[Optional[str]] = mapped_column(Text)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="queued")  # queued|sent|failed
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_msg_org_channel", "org_id", "channel"),)

# ── Audit Logs ─────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    org_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("tenants.id"))
    user_id: Mapped[Optional[str]] = mapped_column(String)
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    log_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_audit_org_ts", "org_id", "created_at"),)
