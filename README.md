# HR Job Portal with AI Resume Matching

Micron/NCG hackathon project. See [`PRD.md`](./PRD.md) for requirements and [`ARCHITECTURE.md`](./ARCHITECTURE.md)
for the full technical design and 24-hour build plan.

**Status:** Feature-complete for the brief and verified end-to-end against a real
Postgres database. Covers both roles: HR (job posting with age eligibility criteria,
ranked applicant review, analytics dashboard) and candidates (registration, profile,
resume upload, search with filters + best-match sorting, apply). Runs locally — this is
not deployed anywhere.

## What's implemented right now

- **Auth**: JWT-based register/login for both roles.
  - **HR registration is restricted to an email-domain allowlist** (`ALLOWED_HR_EMAIL_DOMAINS`)
    — this is what actually stops a candidate from self-registering as HR; it's enforced
    server-side in `app/routers/auth.py`, not just hidden in the UI.
  - **Candidate registration** requires email + phone + password up front, then a separate
    profile-completion step (`PUT /api/candidates/me/profile`) collects personal details
    (DOB, gender, current/preferred location, headline), class 10 and 12 percentages, and
    education (degree, specialization, institution, years, grade) — modeled on what
    Naukri/LinkedIn/Indeed collect. Only gender and headline are optional; everything
    else is required on both client and server.
- **Job CRUD** for HR, with a **search endpoint** (`GET /api/jobs/search`) that supports
  role/skill/location/experience filters, all combinable, and **defaults to sorting by
  highest AI match % first** (`sort=match_desc`).
- **Resume parsing**: PDF/DOCX → skills, experience years, education, certifications,
  project keywords, all via `app/parsing/`, no LLM calls.
- **AI matching engine** (`app/matching/`): the exact weighted formula from the brief
  (Skills 40% / Experience 25% / Role Responsibility 20% / Education 10% / Location 5%),
  using local `sentence-transformers` embeddings for the semantic pieces.
  **Every sub-score has exactly one data source** — skills, experience and role
  relevance come only from the parsed resume; education (degree, class 10 %, class 12 %)
  and location come only from the registration profile. No field is read from both, so
  the two can never disagree about the same candidate.
- **Age eligibility criteria**: HR can set a min/max age per posting. Out-of-range
  candidates are blocked from applying — enforced server-side in
  `routers/applications.py`, not just hidden in the UI.
- **Internships excluded from experience**: `parsing/extractors.py` skips
  intern/trainee/apprentice roles when summing tenure, so a fresher with two
  internships correctly reads as 0 years rather than inflating their seniority.
- **Explainable scores**: every score ships with a deterministic, template-generated
  **plain-language explanation** (`app/matching/summary.py`) — not just a number.
- **Validation on both sides**: every form is validated in the browser for fast feedback
  AND re-validated server-side in `app/schemas.py`, which is the actual gate — the
  browser checks can be bypassed entirely by posting straight to the API.
- **Optional Groq LLM enhancement** (`app/matching/llm_summary.py`): when `GROQ_API_KEY`
  is set, the explanation is rewritten into more natural language by Groq. **Scores are
  never touched** — the local weighted formula stays the sole source of truth for every
  number; the LLM only rephrases the sentence explaining them. Fully fail-safe: no key,
  no network, a rate limit, a timeout, or a stale model ID all fall back silently to the
  template summary, so the app still runs fully offline. Deliberately opt-in per call
  site (`use_llm=True`) — the job-search endpoint scores every open job per request and
  would otherwise fire one LLM call per row. Responses carry an `ai_generated` flag and
  the UI labels AI-written explanations.
- **Synthetic sample data** (`app/seed.py`): 1 HR account, 10 varied job postings, 6
  candidates spanning strong-fit, weak-fit, overqualified, and career-mismatch profiles,
  so match-score sorting is visibly meaningful in a demo.
- **Tests**: `backend/tests/test_scoring.py` — sanity checks on every sub-score plus a
  regression test that a strong-fit resume always outranks a weak-fit one.
- **HR job-posting UI**: dashboard listing all postings (`/hr`), create (`/hr/jobs/new`),
  edit + open/close toggle (`/hr/jobs/[jobId]/edit`), and a ranked applicant view
  (`/hr/jobs/[jobId]/applicants`) showing candidate name/email/phone, match % badge, an
  expandable full explanation, and a shortlist/reject status dropdown
  (`PATCH /api/applications/{id}/status` — added to support this).
- **Candidate job-search UI** (`/candidate/jobs`): role/skill/location/experience filters
  (combinable) + a sort dropdown defaulting to "Best match", match % badges color-coded
  by score band, and a quick-apply button. The detail page (`/candidate/jobs/[jobId]`)
  shows the full weighted breakdown as progress bars (Skills 40% / Experience 25% /
  Role 20% / Education 10% / Location 5%) plus the plain-language summary and an Apply
  button.

## Known issues fixed during build (so you don't hit them again)

- **`passlib`/`bcrypt` incompatibility**: passlib 1.7.4's backend detection breaks on
  `bcrypt>=4.1` (`ValueError: password cannot be longer than 72 bytes`). Pinned to
  `bcrypt==4.0.1` in `requirements.txt`.
- **Pydantic v2 doesn't auto-stringify UUIDs**: SQLAlchemy returns `UUID` objects for
  UUID columns; a Pydantic `str` field does not coerce them automatically and raises a
  validation error. Fixed with a `UUIDStr = Annotated[str, BeforeValidator(str)]` type
  alias used on every `id`/`job_id` field in `app/schemas.py`.
- **Experience extraction double-counted education dates**: the regex that sums
  `YYYY-YYYY` date ranges was matching education dates (e.g. "2016–2020" degree) as if
  they were work tenure, inflating years of experience. Fixed by scoping range-summing
  to a detected "Work Experience" section (`app/parsing/extractors.py`).
- **CORS origin mismatch in local dev**: if your frontend dev server lands on a port
  other than 3000 (Next.js auto-increments if 3000 is taken), set `CORS_ORIGINS` in the
  backend `.env` to match, or it'll fail with a silent "Failed to fetch" in the browser.
  Default now covers both `:3000` and `:3001`.
- **`next@14.2.15` has known CVEs** (Server Actions/middleware/Image Optimizer DoS,
  cache poisoning, etc.). Bumped to `14.2.35`. We deliberately did **not** jump to
  Next.js 15 given the time box — this app uses no Server Actions, middleware, or
  `next/image`, so the remaining advisories (still flagged by `npm audit`) don't apply
  to our actual surface. Worth revisiting post-hackathon.

## Local setup

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit ALLOWED_HR_EMAIL_DOMAINS to your actual org domain(s)
```

`.env` is loaded automatically at startup (via `python-dotenv` in `app/config.py`) — no
need to export variables manually. To enable the optional Groq explanations, add a free
key from [console.groq.com](https://console.groq.com) as `GROQ_API_KEY`; leave it blank
to run fully offline. **Note:** Groq rotates model IDs, and a stale one fails with a 404
that the fallback silently swallows (looks like "the LLM just isn't working") — verify
`GROQ_MODEL` is live on your account with `client.models.list()` if explanations never
show the ✨ AI label.

Start Postgres (either Docker or a local install):

```bash
docker compose up -d          # OR: brew services start postgresql@16
createdb hr_portal            # if not using docker compose, which creates it for you
```

Seed synthetic demo data (also creates tables — no separate migration step needed for local dev):

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/hr_portal"
python -m app.seed
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
pytest tests/ -v
```

**Demo logins after seeding:**
| Role | Email | Password | Notes |
|---|---|---|---|
| HR | `hr@yahoo.com` | `HrPass123!` | Owns all 10 seeded job postings |
| Candidate | `priya.sharma@example.com` | `Candidate123!` | Strong fit for Backend Engineer (~95-100%) |
| Candidate | `vikram.rao@example.com` | `Candidate123!` | Weak fit for all tech roles (marketing background) |

(4 more seeded candidates — see `app/seed.py` for the full list: Arjun/Data Scientist,
Sneha/Frontend, Rahul/fresher, Ananya/overqualified PM.)

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000/api by default
npm run dev
```

If port 3000 is taken, Next.js will pick another port — update the backend's
`CORS_ORIGINS` env var to match, or you'll get a silent CORS failure.

## Alembic migrations (for the actual deployed DB, not local dev)

Local dev uses `Base.metadata.create_all()` via the seed script for speed. For a real
migration history (needed once you deploy and want repeatable schema changes):

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## Deploying (you'll need to do this part yourself — it requires your own accounts)

Full steps are in [`ARCHITECTURE.md`](./ARCHITECTURE.md#8-deployment-plan). Summary:

1. **Render or Railway**: create a Postgres instance, then a web service from `/backend`
   using the included `Dockerfile` (which bakes the `sentence-transformers` model into
   the image at build time so the live demo never depends on a runtime download).
   Set env vars: `DATABASE_URL`, `JWT_SECRET`, `ALLOWED_HR_EMAIL_DOMAINS`, `CORS_ORIGINS`
   (your Vercel URL once you have it).
2. **Vercel**: import `/frontend`, set `NEXT_PUBLIC_API_BASE_URL` to your Render/Railway
   backend URL + `/api`.
3. Run the seed script (or `alembic upgrade head` + your own data) against the live DB.
4. **Free-tier cold starts**: Render/Railway free services spin down after inactivity —
   hit your backend URL a minute before judges arrive to warm it up.

## What's next (per ARCHITECTURE.md §7)

- Candidate resume upload UI (`/candidate/resume`) with parsed-data preview — this is
  the last major screen missing before the whole required-feature loop is UI-complete
- Deploy to Vercel + Render/Railway
- Stretch features (ranked in ARCHITECTURE.md §7): missing-skill highlighting on job
  cards, proactive role recommendations on the candidate dashboard, resume improvement
  tips (HR shortlist/reject status is already done — see above)
