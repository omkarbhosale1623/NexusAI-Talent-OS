// src/lib/adapters.ts
// Maps NexusAI backend (Python/FastAPI snake_case Pydantic) responses
// onto the frontend's existing TypeScript contract (types/index.ts).
// Keeps the polished pre-built UI pages decoupled from backend field-naming.

import type {
  Application, ApplicationStatus, Candidate, DashboardStats,
  Evaluation, Job, JobStatus, Recommendation, Report, ScheduledInterview,
  InterviewRoundType,
} from "@/types";

// ── Job ──────────────────────────────────────────────────────────────────
export function adaptJob(raw: any): Job {
  return {
    id: raw.id,
    title: raw.title,
    department: raw.department ?? "",
    location: raw.location ?? "",
    type: (raw.employment_type === "full_time" ? "onsite" : raw.employment_type) ?? "onsite",
    description: raw.description,
    required_skills: raw.required_skills ?? [],
    experience_min: raw.experience_min ?? 0,
    experience_max: raw.experience_max ?? 0,
    salary_min: raw.salary_min ?? 0,
    salary_max: raw.salary_max ?? 0,
    status: raw.status as JobStatus,
    created_at: raw.created_at,
    applications_count: raw.application_count ?? 0,
    interview_rounds: rawRoundsToConfig(raw.rounds_config),
  };
}

function rawRoundsToConfig(rc: any) {
  if (!rc) return [];
  const labelMap: Record<string, string> = {
    intro: "introduction", technical: "technical",
    behavioral: "behavioral", hr: "hr_culture",
  };
  return Object.entries(rc).map(([key, val]: [string, any]) => ({
    type: (labelMap[key] ?? key) as InterviewRoundType,
    duration_minutes: val.duration_minutes ?? 10,
    focus_areas: val.focus_areas ?? [],
    enabled: val.enabled ?? true,
  }));
}

// ── Candidate ────────────────────────────────────────────────────────────
export function adaptCandidate(raw: any): Candidate {
  return {
    id: raw.id,
    name: raw.full_name,
    email: raw.email,
    phone: raw.phone ?? null,
    resume_url: null, // fetched separately via presigned URL if needed
    parsed_resume: null,
    created_at: raw.created_at,
  };
}

// ── Application ──────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, ApplicationStatus> = {
  applied: "applied",
  screening: "parsing",
  shortlisted: "shortlisted",
  rejected: "rejected",
  interview_scheduled: "scheduled",
  interview_completed: "completed",
  evaluated: "completed",
  hired: "completed",
  offer_sent: "completed",
  withdrawn: "no_show",
};

export function adaptApplication(raw: any): Application {
  return {
    id: raw.id,
    job_id: raw.job_id,
    candidate_id: raw.candidate_id,
    status: STATUS_MAP[raw.status] ?? "applied",
    eligibility_score: raw.eligibility_score != null ? raw.eligibility_score * 100 : null,
    created_at: raw.applied_at,
    candidate: raw.candidate ? adaptCandidate(raw.candidate) : undefined,
  };
}

// ── Interview / Scheduled Interview ─────────────────────────────────────
export function adaptScheduledInterview(raw: any): ScheduledInterview {
  return {
    id: raw.id,
    application_id: raw.application_id,
    scheduled_at: raw.scheduled_at,
    duration_minutes: 60,
    room_token: raw.token,
    status: raw.status === "active" ? "in_progress" : raw.status,
  };
}

// ── Recommendation (backend already sends Title Case matching label) ─────
const REC_MAP: Record<string, Recommendation> = {
  "Strong Hire": "strong_hire",
  "Hire": "hire",
  "Maybe": "maybe",
  "No Hire": "no_hire",
};

export function adaptRecommendation(raw: string): Recommendation {
  return REC_MAP[raw] ?? "maybe";
}

// ── Report / Evaluation ─────────────────────────────────────────────────
export function adaptReport(raw: any): Report {
  const ev = raw.evaluation;
  return {
    id: ev.id,
    interview_id: ev.interview_id,
    round_assessments: Object.entries(ev.round_scores || {}).map(([round, score]) => ({
      round_type: roundKeyToType(round),
      score: score as number,
      observations: [],
      strengths: ev.competency_scores ? Object.keys(ev.competency_scores) : [],
      weaknesses: ev.risk_flags || [],
    })),
    overall_score: ev.overall_score,
    recommendation: adaptRecommendation(ev.recommendation),
    strengths: ev.answer_evaluations?.flatMap((a: any) => a.strengths || []) ?? [],
    improvements: ev.answer_evaluations?.flatMap((a: any) => a.improvements || []) ?? [],
    salary_recommendation: ev.salary_recommendation ?? { min: 0, max: 0, justification: "" },
    pdf_url: ev.report_pdf_s3_key ?? null,
    created_at: ev.created_at,
  };
}

function roundKeyToType(key: string) {
  const map: Record<string, any> = {
    intro: "introduction", technical: "technical",
    behavioral: "behavioral", hr: "hr_culture",
  };
  return map[key] ?? key;
}

// ── Dashboard Stats ──────────────────────────────────────────────────────
export function adaptDashboardStats(raw: any): DashboardStats {
  const p = raw.pipeline || {};
  return {
    total_jobs: raw.active_jobs ?? 0,
    active_jobs: raw.active_jobs ?? 0,
    total_candidates: p.total_applications ?? 0,
    total_interviews: p.interview_completed ?? 0,
    interviews_this_week: raw.interviews_this_week ?? 0,
    avg_score: raw.avg_score ?? 0,
    pass_rate: raw.hire_rate ? raw.hire_rate * 100 : 0,
  };
}
