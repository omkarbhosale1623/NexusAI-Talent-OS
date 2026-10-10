"""NexusAI Talent OS — All Pydantic Schemas"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Enums ─────────────────────────────────────────────────────────────────
class JobStatus(str, Enum):
    DRAFT = "draft"; PUBLISHED = "published"; PAUSED = "paused"
    CLOSED = "closed"; ARCHIVED = "archived"

class EmploymentType(str, Enum):
    FULL_TIME = "full_time"; PART_TIME = "part_time"
    CONTRACT = "contract"; INTERNSHIP = "internship"

class ApplicationStatus(str, Enum):
    APPLIED = "applied"; SCREENING = "screening"; SHORTLISTED = "shortlisted"
    REJECTED = "rejected"; INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"; EVALUATED = "evaluated"
    HIRED = "hired"; OFFER_SENT = "offer_sent"; WITHDRAWN = "withdrawn"

class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"; READY = "ready"; ACTIVE = "active"
    COMPLETED = "completed"; EVALUATED = "evaluated"
    CANCELLED = "cancelled"; NO_SHOW = "no_show"

class Recommendation(str, Enum):
    STRONG_HIRE = "Strong Hire"; HIRE = "Hire"
    MAYBE = "Maybe"; NO_HIRE = "No Hire"

class RoundType(str, Enum):
    INTRO = "intro"; TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"; HR = "hr"

class Difficulty(str, Enum):
    EASY = "easy"; MEDIUM = "medium"; HARD = "hard"

# ── Auth ──────────────────────────────────────────────────────────────────
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str; user_id: str; org_id: str
    full_name: str; email: str; role: str; plan: str

class UserProfile(BaseModel):
    id: str; org_id: str; email: str; full_name: str
    role: str; plan: str; created_at: datetime
    model_config = {"from_attributes": True}

# ── Jobs ──────────────────────────────────────────────────────────────────
class RoundsConfig(BaseModel):
    intro: dict = {"enabled": True, "duration_minutes": 7, "num_questions": 3}
    technical: dict = {"enabled": True, "duration_minutes": 20, "num_questions": 6}
    behavioral: dict = {"enabled": True, "duration_minutes": 15, "num_questions": 4}
    hr: dict = {"enabled": True, "duration_minutes": 10, "num_questions": 3}

class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    experience_min: int = Field(default=0, ge=0)
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    description: str = Field(min_length=50)
    requirements: Optional[str] = None
    nice_to_have: Optional[str] = None
    required_skills: List[str] = []
    nice_to_have_skills: List[str] = []
    eligibility_threshold: float = Field(default=0.60, ge=0, le=1)
    auto_shortlist: bool = True
    rounds_config: Optional[dict] = None
    question_bank_id: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None; department: Optional[str] = None
    location: Optional[str] = None; description: Optional[str] = None
    requirements: Optional[str] = None; required_skills: Optional[List[str]] = None
    salary_min: Optional[int] = None; salary_max: Optional[int] = None
    eligibility_threshold: Optional[float] = None
    rounds_config: Optional[dict] = None; question_bank_id: Optional[str] = None
    status: Optional[str] = None

class JobResponse(BaseModel):
    id: str; org_id: str; title: str; department: Optional[str]
    location: Optional[str]; employment_type: str
    experience_min: int; experience_max: Optional[int]
    salary_min: Optional[int]; salary_max: Optional[int]; salary_currency: str
    description: str; requirements: Optional[str]; nice_to_have: Optional[str]
    required_skills: Optional[List[str]]; nice_to_have_skills: Optional[List[str]]
    status: str; eligibility_threshold: float; auto_shortlist: bool
    rounds_config: Optional[dict]; question_bank_id: Optional[str]
    published_at: Optional[datetime]; created_at: datetime
    application_count: Optional[int] = 0
    model_config = {"from_attributes": True}

# ── Candidates ────────────────────────────────────────────────────────────
class CandidateResponse(BaseModel):
    id: str; org_id: str; full_name: str; email: str
    phone: Optional[str]; linkedin_url: Optional[str]; created_at: datetime
    model_config = {"from_attributes": True}

# ── Applications ──────────────────────────────────────────────────────────
class ApplyRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    years_experience: Optional[float] = None
    expected_salary: Optional[int] = None
    expected_salary_currency: str = "USD"
    cover_letter: Optional[str] = None
    linkedin_url: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: str; org_id: str; job_id: str; candidate_id: str; status: str
    resume_s3_key: Optional[str]; resume_filename: Optional[str]
    years_experience: Optional[float]; expected_salary: Optional[int]
    eligibility_score: Optional[float]; eligibility_breakdown: Optional[dict]
    parsed_resume: Optional[dict]; applied_at: datetime
    updated_at: datetime; candidate: Optional[CandidateResponse] = None
    model_config = {"from_attributes": True}

class EligibilityResponse(BaseModel):
    application_id: str; overall_score: float
    skills_score: float; experience_score: float
    education_score: float; bonus_score: float
    matched_skills: List[str]; missing_skills: List[str]
    recommendation: str  # auto_shortlist | manual_review | auto_reject
    reasoning: str

# ── Scheduling ────────────────────────────────────────────────────────────
class SlotCreate(BaseModel):
    slot_datetime: datetime; duration_minutes: int = 60
    max_bookings: int = 1; timezone: str = "UTC"
    job_id: Optional[str] = None

class SlotResponse(BaseModel):
    id: str; slot_datetime: datetime; duration_minutes: int
    is_available: bool; timezone: str; current_bookings: int; max_bookings: int
    model_config = {"from_attributes": True}

class BookSlotRequest(BaseModel):
    slot_id: str

class ScheduleInviteResponse(BaseModel):
    schedule_token: str; schedule_link: str
    candidate_name: str; job_title: str; expires_at: datetime

# ── Questions ─────────────────────────────────────────────────────────────
class QuestionSchema(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    topic: Optional[str] = None; competency: str = "general"
    difficulty: Difficulty = Difficulty.MEDIUM
    round_type: Optional[str] = None
    expected_answer: Optional[str] = None
    keywords: List[str] = []; follow_up_hints: List[str] = []

class QuestionResponse(BaseModel):
    id: str; bank_id: str; text: str; topic: Optional[str]
    competency: str; difficulty: str; round_type: Optional[str]
    expected_answer: Optional[str]; keywords: Optional[List[str]]
    follow_up_hints: Optional[List[str]]; order_index: int
    model_config = {"from_attributes": True}

class QuestionBankResponse(BaseModel):
    id: str; org_id: str; name: str; description: Optional[str]
    source: str; role_tag: Optional[str]; question_count: int
    is_active: bool; created_at: datetime; questions: List[QuestionResponse] = []
    model_config = {"from_attributes": True}

class GenerateQuestionsRequest(BaseModel):
    job_id: str; application_id: Optional[str] = None
    num_questions: int = Field(default=10, ge=5, le=15)
    bank_name: Optional[str] = None

# ── Interviews ────────────────────────────────────────────────────────────
class ConversationRequest(BaseModel):
    transcript: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    current_round: Optional[str] = None

class ConversationResponse(BaseModel):
    bot_text: str; audio: str; done: bool
    question_index: int; total_questions: int
    current_round: str; round_progress: dict
    is_follow_up: bool = False; follow_up_number: Optional[int] = None
    round_changed: bool = False; new_round: Optional[str] = None

class InterviewResponse(BaseModel):
    id: str; org_id: str; application_id: str; job_id: str; candidate_id: str
    token: str; status: str; scheduled_at: Optional[datetime]
    started_at: Optional[datetime]; completed_at: Optional[datetime]
    current_round: str; current_question_index: int; total_questions: int
    proctoring_enabled: bool; proctoring_risk_score: float
    created_at: datetime
    model_config = {"from_attributes": True}

# ── Evaluation ─────────────────────────────────────────────────────────────
class AnswerEvaluationSchema(BaseModel):
    answer_id: str; question_text: str; answer_text: str; round_type: str
    relevance: float; depth: float; accuracy: float
    communication: float; confidence: float; total_score: float
    rating: str; candidate_feedback: str; detailed_analysis: str
    strengths: List[str]; improvements: List[str]
    model_config = {"from_attributes": True}

class EvaluationResponse(BaseModel):
    id: str; interview_id: str; overall_score: float; overall_rating: str
    recommendation: str; executive_summary: Optional[str]
    hiring_notes: Optional[str]; risk_flags: Optional[List[str]]
    communication: Optional[Dict[str, float]]
    competency_scores: Optional[Dict[str, float]]
    round_scores: Optional[Dict[str, float]]
    skill_gaps: Optional[List[Dict]]
    salary_recommendation: Optional[Dict]
    answer_evaluations: List[AnswerEvaluationSchema] = []
    llm_model_used: Optional[str]; created_at: datetime
    model_config = {"from_attributes": True}

class EvaluationStatusResponse(BaseModel):
    status: str; task_id: Optional[str] = None
    evaluation: Optional[EvaluationResponse] = None

# ── Speech ────────────────────────────────────────────────────────────────
class TranscribeResponse(BaseModel):
    transcript: str; language: Optional[str]; duration_seconds: Optional[float]

class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice: Optional[str] = None

class TTSResponse(BaseModel):
    audio: str  # base64 MP3

# ── Reports ───────────────────────────────────────────────────────────────
class ReportResponse(BaseModel):
    evaluation: EvaluationResponse
    candidate: CandidateResponse
    job_title: str; application_status: str
    proctoring_summary: Dict[str, Any]
    model_config = {"from_attributes": True}

# ── Analytics / Dashboard ─────────────────────────────────────────────────
class PipelineStats(BaseModel):
    total_applications: int; screening: int; shortlisted: int
    interview_scheduled: int; interview_completed: int; evaluated: int; hired: int

class DashboardStats(BaseModel):
    pipeline: PipelineStats; active_jobs: int
    interviews_this_week: int; avg_score: Optional[float]
    hire_rate: Optional[float]; avg_time_to_hire_days: Optional[float]

# ── Proctoring ────────────────────────────────────────────────────────────
class ProctoringEventRequest(BaseModel):
    event_type: str; confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}; timestamp: datetime

# ── Candidate Portal ──────────────────────────────────────────────────────
class PortalAccessResponse(BaseModel):
    candidate_name: str; job_title: str; company_name: str
    application_status: str; interview_status: Optional[str]
    interview_scheduled_at: Optional[datetime]
    can_schedule: bool; can_join_interview: bool
    can_view_report: bool; report_shared: bool

# ── Common ────────────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    items: List[Any]; total: int; page: int; page_size: int; has_next: bool

class ErrorResponse(BaseModel):
    error: str; message: str; request_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str; version: str; environment: str; checks: Dict[str, str]
