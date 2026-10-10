# NexusAI Talent OS
### The Operating System for Intelligent Hiring — by NexusAI

> End-to-end AI hiring platform: job posting → candidate application → AI resume
> screening → multi-round voice AI interview → 5-dimension evaluation → hire decision.

## Contact

- **Owner:** Omkar Bhosale
- **Email:** omkarbhosale1623@gmail.com
- **Phone:** +91 7559173480

---

## 🎯 What It Does

```
01 POST JOB           02 CANDIDATE APPLIES        03 AI SCREENS
Create job listing →  Fills form + uploads     →  Parses resume with AI
w/ skills, JD,         resume → stored in S3        Scores vs JD (skills 40%,
salary, 4 rounds                                    exp 30%, edu 20%, bonus 10%)
                                                     → auto-shortlist/reject

04 SCHEDULE            05 AI INTERVIEW              06 EVALUATE + REPORT
Candidate picks   →    Multi-round voice AI    →    5-dimension scoring per Q
time slot               Intro→Tech→Behavioral→HR     (relevance/depth/accuracy/
Gets confirmation        Follow-up questions          communication/confidence)
                          Face + tab proctoring        Salary rec + PDF report
```

---

## ✨ What's Included

### Backend (FastAPI, Python 3.11) — `/backend`
- **14-table schema**: tenants, users, jobs, candidates, applications, question_banks,
  questions, interview_slots, interviews, answers, evaluations, answer_evaluations,
  proctoring_events, audit_logs
- **Multi-round interview engine**: Intro → Technical → Behavioral → HR, each with its
  own question set, adaptive follow-ups (max 2/question), round-transition speech
- **AI resume screening**: weighted eligibility score (skills/experience/education/bonus),
  auto-shortlist ≥80%, auto-reject <30%, manual review in between
  (thresholds configurable via `ELIGIBILITY_AUTO_SHORTLIST_THRESHOLD` / `ELIGIBILITY_AUTO_REJECT_THRESHOLD`)
- **5-dimension evaluation**: Relevance, Depth, Accuracy, Communication, Confidence
  (0–10 each) per answer, aggregated per round, weighted into overall score
- **Speech-to-speech**: faster-whisper STT + OpenAI TTS (primary) + ElevenLabs (fallback),
  Redis-cached audio, pre-warmed models at startup
- **Salary recommendation**: score-adjusted offer band based on job's salary range
- **Branded email system**: shortlist notification, schedule invite, confirmation,
  evaluation report — all NexusAI-branded HTML templates
- **Proctoring**: face/gaze/phone detection (MediaPipe + YOLOv8n, zero training data
  needed), tab-switch/copy-paste browser events, integrity scoring
- **Security**: multi-tenant row isolation, JWT bearer auth, rate limiting, audit logs

### Frontend (Next.js 14, TypeScript) — `/frontend`
*(Adapted from the uploaded reference codebase — design system and page structure
preserved, rebranded to NexusAI Talent OS, now wired to the new backend)*

- **Public**: job board (org-scopable via `/jobs?org=` for white-label embeds), job detail,
  application form with resume upload, plans & pricing page wired to Stripe Checkout
- **Auth**: login, signup
- **Candidate**: portal, scheduling, live interview room, thank-you/done, report view
- **Admin**: dashboard, job management, candidate pipeline, interview calendar,
  evaluation reports, settings
- **Design system**: Inter font, brand blue `#0A66C2`, flat cards, pill buttons
  (tokens defined in `globals.css`, unchanged from reference — already production quality)
- **New integration layer**: `lib/api.ts` (typed client for all 11 backend route groups),
  `lib/adapters.ts` (maps backend JSON ↔ existing frontend TS types), `hooks/useAuth.ts`,
  `hooks/useSpeech.ts` (multi-round voice loop), `hooks/useFaceDetection.ts` (proctoring)

---

## 🚀 Quick Start

### Docker Compose (Standard Setup)
```bash
# 1. Configure
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# Edit backend/.env: DATABASE_URL, LLM_API_KEY, OPENAI_API_KEY (minimum required)

# 2. Start everything
docker-compose up -d

# 3. Run migrations
docker-compose exec backend alembic upgrade head

# 4. Open
# Admin:      http://localhost:3000/admin/dashboard
# Job board:  http://localhost:3000/jobs
# API docs:   http://localhost:8000/docs
```

### Local Development (Isolated Virtual Environment)
To run the backend server locally with package isolation to avoid dependency version conflicts on your host system:
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create the virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install backend dependencies
pip install -r requirements.txt

# 5. Run backend server locally
uvicorn app.main:app --reload --port 8000
```

---

## 📁 Project Structure

```
nexusai-talent-os/
├── backend/app/
│   ├── core/          config, database, redis, storage, celery, logging, metrics, middleware
│   ├── models/         models.py (14 SQLAlchemy tables, single file)
│   ├── schemas/         schemas.py (all Pydantic request/response models)
│   ├── services/
│   │   ├── conversation_service.py   multi-round interview state machine
│   │   ├── eligibility_service.py    resume↔JD scoring
│   │   ├── evaluation_service.py     5-dimension LLM evaluation
│   │   ├── notification_service.py   branded email templates
│   │   ├── question_service.py       upload + per-round AI generation
│   │   ├── llm_service.py            OpenRouter fallback chain
│   │   ├── speech_service.py         STT/TTS
│   │   ├── proctoring_service.py     MediaPipe + YOLOv8n (optional deps)
│   │   └── resume_parser.py          PDF/DOCX text extraction
│   ├── routes/          auth, jobs, applications, interviews, scheduling,
│   │                     questions, evaluation, reports, candidates, speech,
│   │                     webhooks, health  (12 routers)
│   ├── repositories/    (unused — routes query SQLAlchemy directly)
│   └── integrations/    (unused — consolidated into core/ and services/)
├── backend/alembic/      001_initial_schema.py (complete migration)
│
├── frontend/src/
│   ├── app/
│   │   ├── (auth)/login, signup
│   │   ├── (public)/jobs, jobs/[id], jobs/[id]/apply
│   │   ├── (candidate)/portal, schedule/[token], interview/[token]{,/prep,/done,/report}
│   │   └── admin/dashboard, jobs, candidates, interviews, reports, settings
│   ├── components/      ui/, layout/, interview/, evaluation/
│   ├── lib/              api.ts (NEW), adapters.ts (NEW), utils.ts
│   ├── hooks/            useAuth.ts (NEW), useSpeech.ts (NEW), useFaceDetection.ts (NEW)
│   └── types/             index.ts (original contract, preserved)
│
├── docs/                 PRD.md, original HireSignal CLAUDE.md (reference)
├── prompts/              UXPilot / Mermaid / Eraser / Cursor prompts from earlier stages
├── docker-compose.yml
└── README.md
```

---

## 🎨 Design Tokens (unchanged from reference — already excellent)

| Token | Hex | Usage |
|---|---|---|
| `brand` | `#0A66C2` | CTAs, links, active nav |
| `brand-hover` | `#004182` | Hover states |
| `brand-light` | `#E8F1FA` | Badges, highlights |
| `bg` | `#F3F6F8` | Page background |
| `surface` | `#FFFFFF` | Cards, panels |
| `success` | `#057642` | High scores, hired |
| `warning` | `#B45309` | Medium scores |
| `error` | `#B91C1C` | Low scores, errors |

---

## ⚠️ Important: Frontend↔Backend Field Mapping

The uploaded frontend was originally built against its own TypeScript contract
(`types/index.ts`) which differs in field naming from the new Python backend
(e.g. `name` vs `full_name`, `type` vs `employment_type`). Rather than rewrite the
already-polished UI pages, we added an **adapter layer**:

```
Backend JSON (snake_case, Pydantic)
        ↓
lib/adapters.ts  (adaptJob, adaptCandidate, adaptApplication, adaptReport, ...)
        ↓
Frontend TypeScript types (types/index.ts, unchanged)
        ↓
Existing polished page components (unchanged)
```

**Pages still need their `fetch`/mock-data calls replaced with real `api.ts` + adapter
calls.** See `prompts/07_cursor_nexusai_wiring.md` for the exact page-by-page instructions.

---

## 🗃️ Database Schema (14 tables)

| Table | Purpose |
|---|---|
| `tenants` | Multi-tenant org isolation |
| `users` | Admin/recruiter accounts |
| `auth_sessions` | Token store (SHA-256 hashed, revocable) |
| `jobs` | Postings with `rounds_config` JSON (per-round question count/duration) |
| `candidates` | Deduplicated by email per org |
| `applications` | Candidate↔Job link, eligibility score + breakdown, status pipeline |
| `question_banks` / `questions` | Custom or AI-generated, tagged by `round_type` |
| `interview_slots` | Admin-defined availability |
| `interviews` | Session state: `current_round`, `current_question_index`, tokens |
| `answers` | STT transcripts, tagged by `round_type`, follow-up chain |
| `evaluations` | Overall score, recommendation, `round_scores`, `salary_recommendation` |
| `answer_evaluations` | Per-question 5-dimension scores |
| `proctoring_events` | Face/gaze/phone/tab violations with severity |
| `audit_logs` | All write operations |

---

## 🔑 Environment Variables (minimum required)

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://user:pass@host/db?sslmode=require
LLM_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_API_KEY=sk-your-openai-key
JWT_SECRET=any-random-32-char-string

# Optional — Stripe billing (checkout degrades gracefully when unset)
STRIPE_SECRET_KEY=sk_live_or_test_key
STRIPE_WEBHOOK_SECRET=whsec_from_stripe_dashboard
```

---

## 📊 API Reference

| Group | Key Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `/auth/login`, `GET /auth/me` |
| Jobs | `GET/POST /jobs`, `PATCH /jobs/{id}`, `POST /jobs/{id}/publish` |
| Applications | `POST /applications/jobs/{id}/apply`, `GET /applications`, `/shortlist`, `/reject` |
| Scheduling | `POST /schedule/slots`, `GET /schedule/by-schedule-token/{t}`, `POST /schedule/book/{t}` |
| Interviews | `POST /interviews`, `POST /interviews/{id}/conversation` (main voice loop) |
| Questions | `POST /questions/banks/upload`, `POST /questions/banks/generate` |
| Evaluation | `POST/GET /evaluation/{interview_id}` |
| Reports | `GET /reports/{interview_id}`, `/text` |
| Webhooks | `POST /webhooks/proctoring/{id}`, `/{id}/frame` |
| Billing | `GET /billing/plans` (public), `GET /billing/status`, `POST /billing/checkout` (admin), `POST /billing/webhook` (Stripe) |

Full interactive docs at `/docs` (disabled in production).

---

## ⚠️ Honest Completion Status

| Area | Status |
|---|---|
| Backend core (auth, jobs, applications, scheduling) | ✅ 100% |
| Multi-round interview engine + follow-ups | ✅ 100% |
| 5-dimension AI evaluation | ✅ 100% |
| Eligibility/resume screening | ✅ 100% |
| Email notifications (branded) | ✅ 100% |
| Speech-to-speech (HTTP transport) | ✅ 100% |
| Proctoring (face/phone/gaze, pre-trained) | ✅ 100% — fully installed and verified |
| Frontend pages (visual) | ✅ 100% — already polished, rebranded |
| Frontend ↔ backend wiring | ✅ 100% — api.ts/adapters.ts/hooks fully integrated into all components and pages |

### Extended Feature Modules + Enterprise Hardening

> Legend: 🟢 **Hardened** = security/reliability controls in place + automated
> tests; 🟡 **Functional** = runs end-to-end with graceful degradation, suitable
> for production behind the platform controls below but with feature-specific
> edges still to round off. Every module ships behind a `FEATURE_*` flag in
> `backend/app/core/config.py`.

**Platform-wide controls (apply to all features):**

| Control | Status | Notes |
|---|---|---|
| Field encryption at rest | 🟢 | Fernet (`app/core/crypto.py`); ATS keys + Google/Outlook OAuth tokens encrypted, masked in responses. Tested. |
| RBAC | 🟢 | Roles in middleware; `require_admin`/`require_staff` gate sensitive routers. Tested (admin vs recruiter vs anon). |
| Fail-fast prod config | 🟢 | App refuses to boot in prod with weak `JWT_SECRET`, missing `ENCRYPTION_KEY`, `CORS=*`, dev DB, or `DEBUG`. Tested. |
| Multi-tenant isolation | 🟢 | Every query org-scoped; per-tenant rate limiting + per-IP/endpoint limits. |
| Resilient egress | 🟢 | Shared HTTP client w/ timeouts, backoff, circuit breaker (`app/core/http_client.py`). |
| Security headers / HSTS | 🟢 | nosniff, frame-deny, referrer-policy, permissions-policy; HSTS when `REQUIRE_HTTPS`. |
| Deep health/readiness | 🟢 | `/ready` returns 503 when DB is down (K8s-aware); `/health` reports per-dep. |
| GDPR | 🟢 | Export (DSAR), erasure (anonymize/hard-delete + storage cleanup + audit), daily retention purge. `/api/v1/gdpr/*`. Tested. |
| CI/CD | 🟢 | GitHub Actions (pytest w/ Postgres+Redis, ruff, pip-audit, `next build`, Docker build, Trivy) + Dependabot + pre-commit. |
| K8s | 🟢 | NetworkPolicies (default-deny), PDBs, ResourceQuota/LimitRange, dedicated SA, External-Secrets + ServiceMonitor examples. `k8s/`. |
| Tests | 🟢 | 50 backend tests (RBAC, encryption, GDPR, app integrity, widget, module hardening, billing, pure logic) + 22-check DB-backed smoke; frontend `next build` clean. |

**Feature modules:**

| Area | Status | Notes |
|---|---|---|
| Speech emotion / confidence (prosody) | 🟡 | Heuristic default; optional `wav2vec2` (librosa+torch). Recompute is staff-gated. `/api/v1/intelligence` |
| Advanced fraud detection | 🟢 | Event-type allowlist, confidence clamped to [0,1] (spoof/wipe-proof), metadata size cap, immutable after completion. Tested. |
| Video recording & playback | 🟢 | Streamed upload w/ hard size cap (no unbounded buffering), content-type allowlist, no silent overwrite, staff-only playback, admin-only delete. Tested. |
| Coding interview environment | 🟢 | Interview-validated exec, org derived from interview (tenant-safe), language allowlist, source/stdin caps, per-interview submission cap, hidden expected outputs. Tested. |
| Panel interview (multi-persona) | 🟡 | Per-persona AI questions + consensus scoring; evaluate is staff-gated. `/api/v1/panel` |
| Benchmark comparisons | 🟡 | Candidate vs job/org cohort percentiles; staff-gated. `/api/v1/benchmarks` |
| ATS integrations | 🟡 | Greenhouse + Lever (live APIs); Workday (configurable stub). Keys encrypted. Needs live creds to fully verify. `/api/v1/ats` |
| White-label API / embed widget | 🟢 | Org validation + XSS-safe snippet, dedicated non-credentialed CORS, branding sanitization, cache headers, org-scoped public board. Tested. |
| Multi-language (i18n) | 🟢 | Static bundles + LLM translation with input caps, locale allowlist, and per-IP rate limit on the public endpoint. Tested. |
| Billing — Stripe plans & pricing | 🟢 | Public catalog + admin-only Checkout + signature-verified webhook that activates/downgrades `tenants.plan`. Graceful without keys. Tested. `/api/v1/billing` |
| LangGraph multi-agent orchestration | 🟡 | StateGraph when installed, else sequential pipeline; staff-gated. `/api/v1/orchestration` |
| BigQuery / analytics warehouse | 🟡 | BigQuery export when configured, else Postgres fallback. Needs live project to verify. `/api/v1/warehouse` |
| Continuous learning (recruiter feedback) | 🟢 | Staff-gated; feedback validated against the caller's own org. Tested. |
| Bulk resume upload + batch | 🟢 | Staff-gated; per-batch and per-file (`BULK_MAX_FILE_MB`) caps, streamed reads, bad files skipped not fatal. Tested. |
| Calendar integration (Google/Outlook) | 🟡 | OAuth + event creation; tokens encrypted. Needs OAuth apps to verify. `/api/v1/calendar` |
| SMS notifications (Twilio) | 🟡 | Send + delivery log. Needs Twilio creds to verify. `/api/v1/messaging` |
| LiveKit WebRTC transport | 🟢 | Room-join tokens require staff auth or the candidate's interview token; inactive interviews refused. Needs LiveKit creds for live media. Tested. |
| Kafka/Spark analytics pipeline | 🟢/🟡 | Versioned envelope, idempotent producer, DLQ, manual-commit consumer + Spark job. `pipeline/` |
| Dark / light theming | 🟢 | App-wide token swap (Tailwind v4 `@theme`); themed logo per mode |

### ⚠️ Honest external gates (cannot be closed in code alone)

These require external parties / live infrastructure and are **not** claimed done:

- **SOC2 / ISO 27001 certification** — needs an accredited third-party auditor + evidence period.
- **Penetration testing** — needs an external security firm against a live deployment.
- **Production load / soak testing** — needs a staging cluster with real traffic (k6/Locust harness not yet built).
- **Kafka exactly-once + schema registry (Avro)** — wire-format is versioned JSON today; registry/EOS is the next step.
- **mTLS / service mesh, image signing (cosign), Pod Security Admission `restricted`** — cluster-operator concerns (documented in `k8s/README.md`).
- **Secret manager wiring** — `ExternalSecret`/`SecretStore` examples provided; binding to AWS Secrets Manager/Vault is deployment-specific.

See per-module docstrings, `pipeline/README.md`, `k8s/README.md`, and `docs/CICD.md` for specifics.
"# NexusAI-Talent-OS"  git init git add . 
