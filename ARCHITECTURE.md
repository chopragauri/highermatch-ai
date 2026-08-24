# Architecture & 24-Hour Build Plan — HR Job Portal with AI Resume Matching

Companion doc to [`PRD.md`](./PRD.md). This is the concrete, buildable technical plan — decisive choices, no menus of options unless a tradeoff genuinely matters for a hackathon.

---

## 1. System Architecture

```
┌──────────────────────────┐        HTTPS/JSON         ┌──────────────────────────────────────┐
│  Next.js 14 (App Router) │ ────────────────────────► │  FastAPI (single service, monorepo)   │
│  Vercel                  │ ◄────────────────────────  │  Render/Railway                       │
│                           │                            │                                        │
│  - HR pages               │                           │  /api/auth        (JWT)               │
│  - Candidate pages         │                          │  /api/jobs        (CRUD, search)      │
│  - Fetch w/ JWT bearer      │                        │  /api/resumes     (upload, parse)     │
└──────────────────────────┘                            │  /api/matches     (score retrieval)   │
                                                          │  /api/applications                    │
                                                          │                                        │
                                                          │  ── in-process modules ──             │
                                                          │  parsing/  (pdfplumber, python-docx)  │
                                                          │  matching/ (sentence-transformers,    │
                                                          │             rule-based extractors)    │
                                                          │  scoring/  (weighted formula + summary)│
                                                          └───────────┬────────────────────────────┘
                                                                      │
                                                      ┌───────────────┴───────────────┐
                                                      │                                │
                                            ┌─────────▼─────────┐          ┌───────────▼──────────┐
                                            │ PostgreSQL         │          │ File storage           │
                                            │ (Render/Railway    │          │ Resumes as BYTEA in    │
                                            │  managed Postgres) │          │ Postgres, NOT on       │
                                            │                     │          │ ephemeral web disk     │
                                            └─────────────────────┘          └────────────────────────┘
```

**Key decisions:**

- **Single FastAPI service, no separate microservice for matching.** The AI matching engine is a Python module (`app/matching/`) imported directly into the API process. The embedding model loads once at process startup (module-level singleton), not per-request.
- **File storage: resume bytes stored directly in Postgres (`BYTEA`), not on disk.** Render/Railway free-tier web services have **ephemeral disks** — anything written locally is wiped on every redeploy/restart. Resumes are small (KB-scale), so storing raw bytes in a Postgres column is reliable, zero extra infra, and trivially backed up with the DB. (If time allows post-MVP: swap to Supabase Storage — free, S3-compatible — but do not build this first.)
- **Parsing happens synchronously on upload**, not via a background queue. No Celery/Redis in this stack. Parsing one resume (text extraction + embedding) takes well under 2 seconds locally, so it runs inline in the `POST /api/resumes` handler. This is the one honest tradeoff vs. a production system: at real scale you'd queue it, here synchronous is simpler and fully sufficient.

---

## 2. Database Schema (PostgreSQL)

Pragmatic choice: **structured columns for anything filtered/sorted on** (skills array, years_experience, location), **JSONB for the rest** of the parsed resume detail (education list, certifications, sub-score breakdowns). Avoids hours spent normalizing nested resume fields into their own tables for structure nobody queries independently in a 24h app.

```sql
-- users: both HR and candidates in one table, differentiated by role
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('hr', 'candidate')),
    full_name       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- job_postings
CREATE TABLE job_postings (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hr_user_id                  UUID NOT NULL REFERENCES users(id),
    title                       TEXT NOT NULL,
    responsibilities            TEXT NOT NULL,               -- freeform JD body, used for embedding
    required_skills             TEXT[] NOT NULL DEFAULT '{}', -- normalized lowercase skill tokens
    min_experience_yrs          NUMERIC(4,1) NOT NULL DEFAULT 0,
    max_experience_yrs          NUMERIC(4,1),                 -- nullable = no upper bound
    required_education          TEXT,                         -- e.g. "Bachelor's", "Master's"
    location                    TEXT NOT NULL,                -- e.g. "Bengaluru", "Remote"
    job_type                    TEXT NOT NULL CHECK (job_type IN ('full-time','part-time','contract','internship')),
    status                      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
    responsibilities_embedding  VECTOR(384),                  -- see note below re: pgvector
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_status ON job_postings(status);
CREATE INDEX idx_jobs_location ON job_postings(location);
CREATE INDEX idx_jobs_skills ON job_postings USING GIN(required_skills);

-- resumes: one row per uploaded resume (re-upload -> new row, is_active flags latest)
CREATE TABLE resumes (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_user_id         UUID NOT NULL REFERENCES users(id),
    file_name                 TEXT NOT NULL,
    file_bytes                BYTEA NOT NULL,
    file_mime                 TEXT NOT NULL,
    raw_text                  TEXT NOT NULL,                  -- extracted plaintext, for re-embedding
    parsed_skills              TEXT[] NOT NULL DEFAULT '{}',
    parsed_experience_yrs       NUMERIC(4,1),
    parsed_education             JSONB NOT NULL DEFAULT '[]',  -- [{degree, field, institution, tier}]
    parsed_certifications         TEXT[] NOT NULL DEFAULT '{}',
    parsed_projects_keywords      TEXT[] NOT NULL DEFAULT '{}',
    resume_embedding                VECTOR(384),
    is_active                        BOOLEAN NOT NULL DEFAULT true,
    created_at                        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_resumes_candidate ON resumes(candidate_user_id) WHERE is_active;

-- applications: candidate applies to a job; also caches the match record
CREATE TABLE applications (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                 UUID NOT NULL REFERENCES job_postings(id),
    candidate_user_id      UUID NOT NULL REFERENCES users(id),
    resume_id              UUID NOT NULL REFERENCES resumes(id),
    match_score_total       NUMERIC(5,2) NOT NULL,            -- 0-100
    match_score_breakdown    JSONB NOT NULL,                   -- {skills: {...}, experience: {...}, ...}
    match_summary_text        TEXT NOT NULL,                   -- human-readable generated summary
    status                     TEXT NOT NULL DEFAULT 'applied' CHECK (status IN ('applied','viewed','shortlisted','rejected')),
    applied_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(job_id, candidate_user_id)
);
CREATE INDEX idx_applications_job ON applications(job_id);
CREATE INDEX idx_applications_candidate ON applications(candidate_user_id);
```

**On `VECTOR(384)` / pgvector:** `all-MiniLM-L6-v2` produces 384-dim embeddings. `pgvector` can be installed on both Render and Railway managed Postgres (`CREATE EXTENSION vector;`). **Decisive call: use pgvector for storage only — do NOT rely on DB-side vector search.** At hackathon scale (dozens–hundreds of rows), pull embeddings into Python and compute cosine similarity with numpy. This avoids debugging pgvector index/operator quirks under time pressure. If `pgvector` install fails for any reason, fall back to a plain `FLOAT4[]`/JSON array column — functionally identical. **Decide this in hour 1, don't revisit.**

**Match score computed at apply-time, cached in `applications`.** Search-time scores (browsing, not yet applied) are computed live per-request — see API section below; only `POST /api/applications` persists a snapshot.

---

## 3. Resume Parsing Pipeline

| Step | Library | Notes |
|---|---|---|
| PDF text extraction | `pdfplumber` | Handles text-based PDFs. Fallback to `PyPDF2` if `pdfplumber` returns empty text. |
| DOCX text extraction | `python-docx` | Iterate `document.paragraphs` + tables (skills are often tabular). |
| Skill extraction | Static skills taxonomy (`app/matching/skills_taxonomy.py`, ~300–500 common tech + soft skills) + case-insensitive word-boundary regex matching against `raw_text` | No spaCy NER needed — keyword matching against a curated list is faster to build, deterministic, and sufficient. |
| Experience years | Regex `r'(\d+)\+?\s*years?\s*(of)?\s*experience'` **plus** date-range detection in a "Work Experience" section (`r'(20\d{2})\s*[-–—to]+\s*(20\d{2}|present)'`), summed | Take the max of the two heuristics — resumes are inconsistent. |
| Education | Keyword match (`"B.Tech", "B.E.", "Bachelor", "M.Tech", "Master", "MBA", "PhD", "Diploma"`) mapped to tier (Diploma=1, Bachelor=2, Master=3, PhD=4) | Store as `parsed_education: [{degree, field?, tier}]`. |
| Certifications | Keyword scan (`"certified"`, `"certification"`, known acronyms: AWS, PMP, CISSP, Scrum, etc.) | Simple substring capture into `parsed_certifications`. |
| Project/keyword extraction | Reuse skills-taxonomy hits found specifically within a detected "Projects" section | Keep cheap — feeds the role-relevance signal, doesn't need its own weight. |
| Semantic embedding | `sentence-transformers`, model `all-MiniLM-L6-v2` (~80MB, CPU-friendly) — **bake into the Docker image at build time**, not fetched at first request, so the live demo never depends on runtime internet access | Embed (a) whole resume `raw_text` → `resume_embedding`, (b) job `responsibilities` → `responsibilities_embedding`. Cosine similarity = role-relevance signal. |

**Pipeline (`backend/app/parsing/pipeline.py`):**
```
extract_text(file_bytes, mime) -> raw_text
  -> extract_skills(raw_text)
  -> extract_experience_years(raw_text)
  -> extract_education(raw_text)
  -> extract_certifications(raw_text)
  -> extract_project_keywords(raw_text)
  -> embed(raw_text)
=> ParsedResume -> persisted to `resumes` row
```
Runs synchronously inside `POST /api/resumes`.

---

## 4. Match Scoring Algorithm

Weights are fixed by the brief: **Skills 40 / Experience 25 / Role Responsibility 20 / Education 10 / Location 5.**

```python
def compute_match(resume: ParsedResume, job: JobPosting) -> MatchResult:
    skills_score, skills_detail   = score_skills(resume.parsed_skills, job.required_skills)
    experience_score, exp_detail  = score_experience(resume.parsed_experience_yrs, job.min_experience_yrs, job.max_experience_yrs)
    role_score, role_detail       = score_role_responsibility(resume.resume_embedding, job.responsibilities_embedding)
    education_score, edu_detail   = score_education(resume.parsed_education, resume.parsed_certifications, job.required_education)
    location_score, loc_detail    = score_location(candidate_preferred_location, job.location)

    total = (skills_score * 0.40 + experience_score * 0.25 +
             role_score * 0.20 + education_score * 0.10 + location_score * 0.05)

    summary = generate_summary(skills_detail, exp_detail, role_detail, edu_detail, loc_detail, total)
    return MatchResult(total=round(total, 2), breakdown={...}, summary=summary)
```

**Sub-score formulas (each normalized to 0–100 before weighting):**

1. **Skills (40%)** — exact match: lowercase both sides, `matched = required ∩ resume`. Semantic fallback for synonyms (e.g. "JS" vs "JavaScript", "Postgres" vs "PostgreSQL"): for leftover unmatched required skills, embed and compare against leftover unmatched resume skills with the same MiniLM model; count matched if cosine similarity > 0.75. `score = 100 * matched_count / required_count` (100 if no required skills). Detail: `{matched, missing, matched_count, required_count}`.

2. **Experience (25%)** — band-based: within `[min, max]` → 100. Below min → `100 * max(0, years/min)` (linear ramp, floor 0). Above max (overqualified) → mild penalty `100 - min(20, (years - max) * 5)`, floor 80. Detail: `{resume_years, required_min, required_max, verdict}`.

3. **Role Responsibility (20%)** — `cosine_similarity(resume_embedding, responsibilities_embedding)`, rescaled: `score = 100 * clamp((cos_sim - 0.2) / (0.7 - 0.2), 0, 1)` so realistic similarity ranges map usefully to 0–100. **Calibrate the 0.2/0.7 bounds against 2–3 real sample resumes during build (hour 8–14) — this is the one formula worth a quick empirical sanity check before demo.**

4. **Education/Certification (10%)** — tier compare: resume tier ≥ required tier → 70 pts, else `70 * (resume_tier/required_tier)`. Certification bonus: `+30` if resume has a cert relevant to the job title/skills, else `+0`. Cap at 100.

5. **Location/Other Fit (5%)** — `job.location == "remote"` → 100. Exact case-insensitive match to candidate's preferred location → 100. No preference set → 60 (neutral). Mismatch → 20 (not zero — weight is only 5%, still let it surface).

**Human-readable summary (`generate_summary`)** — pure template-fill from the sub-score details, **no LLM call**:

```python
def generate_summary(skills, exp, role, edu, loc, total) -> str:
    parts = [
        f"Skills: {skills['matched_count']}/{skills['required_count']} matched"
        + (f", missing: {', '.join(skills['missing'])}" if skills['missing'] else ""),
        f"Experience: {exp['resume_years']} yrs vs required "
        + (f"{exp['required_min']}-{exp['required_max']}" if exp['required_max'] else f"{exp['required_min']}+")
        + f" {'✓' if exp['verdict']=='meets' else ('↑' if exp['verdict']=='exceeds' else '✗')}",
        f"Role relevance: {role['rescaled_score']:.0f}% similarity to responsibilities",
        f"Education: {edu['highest_degree'] or 'none listed'}"
        + (", relevant certification found" if edu['has_relevant_cert'] else ""),
        f"Location: {loc['match_type']}",
    ]
    return " | ".join(parts) + f" → Overall match: {total:.0f}%"
```

Example: `"Skills: 8/10 matched, missing: Kubernetes, Terraform | Experience: 4.0 yrs vs required 3-5 ✓ | Role relevance: 71% similarity to responsibilities | Education: Bachelor's, relevant certification found | Location: exact → Overall match: 78%"`

---

## 5. API Design (FastAPI, prefix `/api`)

```
POST   /api/auth/register              {email, password, full_name, role}   -> {access_token, user}
POST   /api/auth/login                 {email, password}                     -> {access_token, user}
GET    /api/auth/me                    (JWT)                                 -> current user profile

# HR job CRUD
POST   /api/jobs                       (HR only) create posting
GET    /api/jobs                       (HR only) list own postings
GET    /api/jobs/{job_id}              get single posting detail
PUT    /api/jobs/{job_id}              (HR only, owner) edit posting
PATCH  /api/jobs/{job_id}/status       (HR only, owner) {status: "closed"}    -> close posting
GET    /api/jobs/{job_id}/applicants   (HR only, owner) applicants + match scores, sorted by match desc

# Candidate resume
POST   /api/resumes                    (candidate) multipart upload -> triggers parsing, returns parsed data
GET    /api/resumes/me                 (candidate) latest active resume + parsed fields

# Candidate job search — core UX requirement: default sort = match % desc, filters combinable
GET    /api/jobs/search
    query params: role, skill, location, min_experience, max_experience,
                   sort=match_desc (default) | newest | experience_asc
    -> live match score per open job against candidate's active resume, sorted per `sort`

# Applications
POST   /api/applications               (candidate) {job_id} -> persists application + score snapshot
GET    /api/applications/me            (candidate) own applications with scores/status

# Direct match lookup (used by "why this score" detail view)
GET    /api/matches/{job_id}           (candidate) recompute/retrieve live match score + summary
```

Auth: JWT bearer (`python-jose`/`PyJWT`), password hashing via `passlib[bcrypt]`. Role guard via a FastAPI dependency (`require_role("hr")`).

---

## 6. Frontend Pages (Next.js App Router)

**Public / auth:** `/` · `/login` · `/register` (role toggle: HR vs Candidate)

**HR flow:**
- `/hr/dashboard` — own postings, status, applicant counts
- `/hr/jobs/new` — create posting form
- `/hr/jobs/[jobId]/edit` — edit / close posting
- `/hr/jobs/[jobId]/applicants` — applicants sorted by match % desc, expandable summary per row

**Candidate flow:**
- `/candidate/dashboard` — resume status, recent applications
- `/candidate/resume` — upload/replace resume, shows parsed preview for confirmation
- `/candidate/jobs` — search: filter bar (role/skill/location/experience) + sort dropdown (default "Best Match") + match % badges
- `/candidate/jobs/[jobId]` — job detail + full match breakdown + Apply
- `/candidate/applications` — applied jobs with status + score

Auth token: localStorage is acceptable for a 24h hackathon demo (not production-grade), sent as `Authorization: Bearer` via a shared `lib/api.ts` wrapper.

---

## 7. 24-Hour Task Breakdown (team of 3–4: 1 backend, 1 frontend, 1 AI/matching, 1 floating/full-stack+DevOps)

### Must-ship (Hours 0–16)

**Hours 0–1 — Setup**
Init monorepo (`/frontend` Next.js+TS+Tailwind, `/backend` FastAPI+SQLAlchemy/Alembic). Provision Render/Railway Postgres **immediately** — this is the most likely source of surprise friction, don't leave it for later. Agree on schema (§2), create the Alembic migration. Push scaffolds to GitHub, connect Vercel + Render/Railway now so the deploy pipe is proven early, not at hour 20.

**Hours 1–4 — Auth + core CRUD backend**
`users` table, register/login/JWT, role guard. `job_postings` CRUD. Seed script with 8–10 sample jobs across varied locations/skills for demo data.

**Hours 1–6 — AI matching module (parallel track)**
Build `app/parsing/` (extraction + regex extractors), test against 3–5 sample resumes. Build the skills taxonomy. Integrate `sentence-transformers`, verify offline load (cache/bake the model now). Implement the 5 sub-score functions + `generate_summary`, sanity-test against sample data.

**Hours 4–8 — Resume upload + search endpoints**
`POST /api/resumes` wired to parsing. `GET /api/jobs/search` with filters + live scoring + default `sort=match_desc`. `POST /api/applications`, `GET /api/jobs/{id}/applicants`, `GET /api/matches/{job_id}`.

**Hours 4–12 — Frontend build (parallel track)**
Auth pages, HR dashboard + job forms, candidate dashboard + resume upload + job search (filter bar + sort + match badges) + application flow + HR applicants view. Build against an API contract agreed in hour 1 so frontend isn't blocked on backend completion.

**Hours 12–16 — Integration**
Wire real API base URL, fix contract mismatches, full manual E2E test: register HR → post job → register candidate → upload resume → search → see match % + summary → apply → HR sees applicant sorted by match. **By hour 16 the full required-feature loop must work end-to-end locally.**

### Hours 16–20 — Deployment
Deploy FastAPI + Postgres to Render/Railway, Next.js to Vercel (see §8). Fix CORS/env vars, run migrations against the live DB, re-seed demo data live. Smoke test against live URLs, not localhost.

### Hours 20–23 — Polish + stretch (only if ahead of schedule)
Ranked by effort:impact — do in this order if time remains:
1. **Missing-skill highlighting** on candidate job cards (near-free, data already computed)
2. **HR shortlist/reject status** on applicants (column already exists)
3. **Role recommendations** on candidate dashboard — reuse the scoring function against all open jobs, no new algorithm
4. **Resume improvement tips** — template-generated from missing-skills data
5. HR analytics dashboard (skip unless truly ahead)
6. Dark mode (skip unless literally nothing else is left)

### Hours 23–24 — Demo prep
Seed 2–3 demo accounts (1 HR, 2 candidates with contrasting resumes) so match-score differentiation is visually obvious. Script a 90-second demo: post job → candidate search sorted by match → open breakdown → apply → HR sees ranked applicants. Confirm both live URLs work from a fresh incognito window.

---

## 8. Deployment Plan

**Backend + DB (Render, or swap to Railway):**
1. Create a Render **PostgreSQL** instance first — note internal + external connection strings.
2. `CREATE EXTENSION IF NOT EXISTS vector;` if using pgvector; otherwise use plain array columns (§2).
3. Create a Render **Web Service** from `/backend`: build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Env vars: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS` (Vercel URL).
5. **Bake the embedding model into the image at build time** (`python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` during the Docker build) so no runtime HuggingFace fetch is ever needed at demo time.
6. Run Alembic migrations against the live `DATABASE_URL`.
7. Resumes as `BYTEA` in Postgres sidesteps the ephemeral-disk problem entirely — no separate object storage needed for MVP.

**Frontend (Vercel):**
1. Import `/frontend` as a Vercel project.
2. Env var: `NEXT_PUBLIC_API_BASE_URL=https://<render-service>.onrender.com/api`.
3. Deploy — Vercel's `*.vercel.app` URL is the judge-facing link.

**CORS:** explicit `allow_origins=[CORS_ORIGINS]` (Vercel URL + `http://localhost:3000` for dev) — do not use `"*"` with credentials, and being explicit avoids a last-minute CORS debugging session.

**Free-tier caveat:** Render/Railway free services spin down after inactivity (~30–50s cold start). **Hit the backend URL yourself a minute or two before judges arrive** to warm it up — put this in the demo runbook.

---

### Critical files to build first
- `backend/app/matching/scoring.py` — the 5 weighted sub-scores + `generate_summary`
- `backend/app/parsing/pipeline.py` — resume extraction orchestration
- `backend/app/models.py` / Alembic migration — schema from §2
- `backend/app/routers/jobs.py` — `/api/jobs/search` with filters + default match-desc sort
- `frontend/app/candidate/jobs/page.tsx` — the primary demoed screen
