// src/lib/api.ts — NexusAI Talent OS API client
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Token management ────────────────────────────────────────────────────
export const getToken = (): string | null =>
  typeof window !== "undefined" ? localStorage.getItem("nexusai_token") : null;

export const setToken = (t: string): void => {
  if (typeof window !== "undefined") localStorage.setItem("nexusai_token", t);
};

export const clearToken = (): void => {
  if (typeof window !== "undefined") localStorage.removeItem("nexusai_token");
};

// ── Core fetch wrapper ───────────────────────────────────────────────────
async function apiFetch<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const isForm = options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(!isForm && { "Content-Type": "application/json" }),
    ...(token && { Authorization: `Bearer ${token}` }),
    ...((options.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (res.status === 204) return null as T;

  const data = await res.json().catch(() => ({ message: res.statusText }));
  if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  return data as T;
}

async function apiText(path: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

const GET    = <T = any>(p: string) => apiFetch<T>(p);
const POST   = <T = any>(p: string, body?: any) =>
  apiFetch<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const PATCH  = <T = any>(p: string, body?: any) =>
  apiFetch<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined });
const DELETE = <T = any>(p: string) => apiFetch<T>(p, { method: "DELETE" });
const FORM   = <T = any>(p: string, fd: FormData) => apiFetch<T>(p, { method: "POST", body: fd });

// ── API surface ──────────────────────────────────────────────────────────
export const api = {
  // ── Auth ──────────────────────────────────────────────────────────────
  signup: (body: { email: string; password: string; full_name: string; company_name: string }) =>
    POST("/auth/signup", body),
  login: (body: { email: string; password: string }) => POST("/auth/login", body),
  me: () => GET("/auth/me"),
  signout: () => POST("/auth/signout"),

  // ── Jobs ──────────────────────────────────────────────────────────────
  listJobs: (params: Record<string, any> = {}) =>
    GET(`/jobs?${new URLSearchParams(params as any)}`),
  getJob: (id: string) => GET(`/jobs/${id}`),
  createJob: (body: any) => POST("/jobs", body),
  updateJob: (id: string, body: any) => PATCH(`/jobs/${id}`, body),
  publishJob: (id: string) => POST(`/jobs/${id}/publish`),
  archiveJob: (id: string) => POST(`/jobs/${id}/archive`),
  parseJd: (text?: string, file?: File) => {
    const fd = new FormData();
    if (text) fd.append("text", text);
    if (file) fd.append("file", file);
    return FORM("/jobs/parse-jd", fd);
  },

  // ── Applications ──────────────────────────────────────────────────────
  applyToJob: (jobId: string, formData: FormData) => FORM(`/applications/jobs/${jobId}/apply`, formData),
  listApplications: (params: Record<string, any> = {}) =>
    GET(`/applications?${new URLSearchParams(params as any)}`),
  getApplication: (id: string) => GET(`/applications/${id}`),
  shortlistApplication: (id: string) => POST(`/applications/${id}/shortlist`),
  rejectApplication: (id: string) => POST(`/applications/${id}/reject`),
  getEligibility: (id: string) => GET(`/applications/${id}/eligibility`),

  // ── Scheduling ────────────────────────────────────────────────────────
  createSlot: (body: any) => POST("/schedule/slots", body),
  listSlots: (params: Record<string, any> = {}) =>
    GET(`/schedule/slots?${new URLSearchParams(params as any)}`),
  getScheduleInfo: (token: string) => GET(`/schedule/by-schedule-token/${token}`),
  bookSlot: (token: string, slotId: string) => POST(`/schedule/book/${token}`, { slot_id: slotId }),
  sendScheduleInvite: (interviewId: string) => POST(`/schedule/send-invite/${interviewId}`),

  // ── Question Banks ────────────────────────────────────────────────────
  uploadQuestionBank: (file: File, bankName: string, description?: string, roleTag?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("bank_name", bankName);
    if (description) fd.append("description", description);
    if (roleTag) fd.append("role_tag", roleTag);
    return FORM("/questions/banks/upload", fd);
  },
  generateQuestions: (jobId: string, applicationId?: string, numQuestions = 16, bankName?: string) => {
    const fd = new FormData();
    fd.append("job_id", jobId);
    if (applicationId) fd.append("application_id", applicationId);
    fd.append("num_questions", String(numQuestions));
    if (bankName) fd.append("bank_name", bankName);
    return FORM("/questions/banks/generate", fd);
  },
  listQuestionBanks: (page = 1) => GET(`/questions/banks?page=${page}`),
  getQuestionBank: (id: string) => GET(`/questions/banks/${id}`),
  deleteQuestionBank: (id: string) => DELETE(`/questions/banks/${id}`),

  // ── Interviews ────────────────────────────────────────────────────────
  createInterview: (applicationId: string) =>
    POST(`/interviews?application_id=${applicationId}`),
  listInterviews: (params: Record<string, any> = {}) =>
    GET(`/interviews?${new URLSearchParams(params as any)}`),
  getInterview: (id: string) => GET(`/interviews/${id}`),
  getInterviewByToken: (token: string) => GET(`/interviews/by-token/${token}`),
  startInterview: (id: string) => POST(`/interviews/${id}/start`),
  conversationStep: (id: string, transcript: string | null, currentRound?: string) =>
    POST(`/interviews/${id}/conversation`, { transcript, current_round: currentRound }),
  completeInterview: (id: string) => POST(`/interviews/${id}/complete`),

  // ── Evaluation ────────────────────────────────────────────────────────
  triggerEvaluation: (interviewId: string) => POST(`/evaluation/${interviewId}`),
  getEvaluation: (interviewId: string) => GET(`/evaluation/${interviewId}`),

  // ── Reports ───────────────────────────────────────────────────────────
  getReport: (interviewId: string) => GET(`/reports/${interviewId}`),
  getReportText: (interviewId: string) => apiText(`/reports/${interviewId}/text`),

  // ── Candidates ────────────────────────────────────────────────────────
  listCandidates: (page = 1) => GET(`/candidates?page=${page}`),
  getCandidate: (id: string) => GET(`/candidates/${id}`),
  getCandidatePortal: (token: string) => GET(`/candidates/portal/${token}`),

  // ── Speech ────────────────────────────────────────────────────────────
  transcribe: (blob: Blob) => {
    const fd = new FormData();
    fd.append("file", blob, "audio.webm");
    return FORM("/speech/transcribe", fd);
  },
  tts: (text: string, voice?: string) => POST("/speech/tts", { text, voice }),

  // ── Dashboard analytics ─────────────────────────────────────────────
  dashboard: () => GET("/analytics/dashboard"),

  // ── Admin org settings ──────────────────────────────────────────────
  updateOrgSettings: (body: any) =>
    apiFetch("/admin/org/settings", { method: "PATCH", body: JSON.stringify(body) }),

  // ── Admin team ──────────────────────────────────────────────────────
  listTeam: () => GET("/admin/team"),

  // ── Evaluation polling helper ───────────────────────────────────────
  pollEvaluation: async (interviewId: string, maxWaitMs = 60000): Promise<any> => {
    const start = Date.now();
    while (Date.now() - start < maxWaitMs) {
      const r = await apiFetch<any>(`/reports/${interviewId}`).catch(() => null);
      if (r) return r;
      await new Promise(res => setTimeout(res, 3000));
    }
    throw new Error("Evaluation timed out");
  },

  // ── Intelligence: prosody / emotion + fraud detection ──────────────────
  getProsody: (iv: string) => GET(`/intelligence/${iv}/prosody`),
  analyzeIntelligence: (iv: string) => POST(`/intelligence/${iv}/analyze`),
  reportFraudEvent: (iv: string, eventType: string, metadata?: any) =>
    POST(`/intelligence/${iv}/fraud-event`, { event_type: eventType, metadata }),
  getFraudSummary: (iv: string) => GET(`/intelligence/${iv}/fraud-summary`),

  // ── Video recording / playback ─────────────────────────────────────────
  uploadRecording: (iv: string, blob: Blob, durationS?: number) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.webm");
    if (durationS != null) fd.append("duration_s", String(durationS));
    return FORM(`/recordings/${iv}/upload`, fd);
  },
  getRecordingPlayback: (iv: string) => GET(`/recordings/${iv}/playback`),
  getRecordingMeta: (iv: string) => GET(`/recordings/${iv}/meta`),
  deleteRecording: (iv: string) => DELETE(`/recordings/${iv}`),

  // ── Coding interview ───────────────────────────────────────────────────
  listCodingProblems: (jobId?: string) =>
    GET(`/coding/problems${jobId ? `?job_id=${jobId}` : ""}`),
  runCode: (iv: string, body: { language: string; source: string; stdin?: string; problem_id?: string }) =>
    POST(`/coding/${iv}/run`, body),
  submitCode: (iv: string, body: { language: string; source: string; problem_id: string }) =>
    POST(`/coding/${iv}/submit`, body),
  listCodingSubmissions: (iv: string) => GET(`/coding/${iv}/submissions`),

  // ── Panel interview mode ───────────────────────────────────────────────
  getPanelPersonas: (iv: string) => GET(`/panel/${iv}/personas`),
  panelQuestion: (iv: string, personaIndex: number, asked?: string[]) =>
    POST(`/panel/${iv}/question`, { persona_index: personaIndex, asked }),
  panelEvaluate: (iv: string) => POST(`/panel/${iv}/evaluate`),

  // ── Benchmarks ─────────────────────────────────────────────────────────
  getBenchmark: (iv: string) => GET(`/benchmarks/${iv}`),

  // ── ATS integrations ───────────────────────────────────────────────────
  listAtsConnections: () => GET("/ats/connections"),
  saveAtsConnection: (body: { provider: string; api_key: string; base_url?: string; config?: any }) =>
    POST("/ats/connections", body),
  deleteAtsConnection: (id: string) => DELETE(`/ats/connections/${id}`),
  testAts: (provider: string) => POST(`/ats/${provider}/test`),
  listAtsJobs: (provider: string) => GET(`/ats/${provider}/jobs`),
  pushCandidateToAts: (provider: string, applicationId: string) =>
    POST(`/ats/${provider}/push-candidate`, { application_id: applicationId }),

  // ── White-label widget ─────────────────────────────────────────────────
  getWidgetConfig: (orgId: string) => GET(`/widget/config/${orgId}`),
  getWidgetEmbed: (orgId: string) => GET(`/widget/embed/${orgId}?format=json`),

  // ── i18n ───────────────────────────────────────────────────────────────
  listLocales: () => GET("/i18n/locales"),
  getLocaleBundle: (locale: string) => GET(`/i18n/bundle/${locale}`),
  translate: (text: string, targetLocale: string) =>
    POST("/i18n/translate", { text, target_locale: targetLocale }),

  // ── LangGraph orchestration ────────────────────────────────────────────
  orchestrationStatus: () => GET("/orchestration/status"),
  runOrchestration: (iv: string) => POST(`/orchestration/${iv}/run`),

  // ── Warehouse / analytics ──────────────────────────────────────────────
  warehouseStatus: () => GET("/warehouse/status"),
  warehouseMetrics: (preset: string) => GET(`/warehouse/metrics?preset=${preset}`),
  warehouseBackfill: () => POST("/warehouse/backfill"),

  // ── Continuous learning ────────────────────────────────────────────────
  submitFeedback: (body: {
    interview_id: string; recruiter_decision: string;
    recruiter_score?: number; rating?: number; notes?: string;
    dimension_corrections?: any;
  }) => POST("/learning/feedback", body),
  getLearningStats: () => GET("/learning/stats"),
  getCalibration: () => GET("/learning/calibration"),

  // ── Bulk resume upload ─────────────────────────────────────────────────
  bulkUpload: (jobId: string, files: File[]) => {
    const fd = new FormData();
    fd.append("job_id", jobId);
    files.forEach((f) => fd.append("files", f));
    return FORM("/bulk/upload", fd);
  },
  bulkStatus: () => GET("/bulk/status"),

  // ── Calendar integration ───────────────────────────────────────────────
  listCalendarConnections: () => GET("/calendar/connections"),
  connectGoogleCalendar: () => GET("/calendar/google/connect"),
  connectOutlookCalendar: () => GET("/calendar/outlook/connect"),
  createCalendarEvent: (iv: string) => POST(`/calendar/event/${iv}`),
  deleteCalendarConnection: (id: string) => DELETE(`/calendar/connections/${id}`),

  // ── SMS / messaging ────────────────────────────────────────────────────
  sendSms: (to: string, body: string) => POST("/messaging/sms", { to, body }),
  listMessages: () => GET("/messaging/messages"),
  sendSmsInvite: (iv: string) => POST(`/messaging/interview/${iv}/sms-invite`),

  // ── LiveKit WebRTC ─────────────────────────────────────────────────────
  livekitStatus: () => GET("/livekit/status"),
  // interviewToken = candidate's interview link token (required when not
  // authenticated as staff — the backend refuses anonymous room joins).
  getLivekitToken: (iv: string, identity: string, interviewToken?: string) =>
    POST(`/livekit/${iv}/token`, { identity, interview_token: interviewToken }),

  // ── Billing (Stripe) ───────────────────────────────────────────────────
  getPlans: () => GET("/billing/plans"),
  getBillingStatus: () => GET("/billing/status"),
  createCheckout: (plan: string) => POST("/billing/checkout", { plan }),
};

// ── Audio helper — CRITICAL: always decode as audio/mpeg (NOT audio/wav) ──
export function playBase64Audio(b64: string): Promise<void> {
  return new Promise((resolve) => {
    const audio = new Audio(`data:audio/mpeg;base64,${b64}`);
    audio.onended = () => resolve();
    audio.onerror = () => { console.warn("Audio playback error"); resolve(); };
    audio.play().catch((e) => { console.warn("Audio play() blocked:", e); resolve(); });
  });
}
