# PRD — HR Job Portal with AI Resume Matching

**Hackathon:** Micron / NCG Technical Problem Statements
**Time box:** < 24 hours (build + deploy + demo)
**Status:** Draft v1

---

## 1. Problem Statement

Build a web application for HR teams to post job openings and allow employees or candidates to register, upload resumes, search jobs, and see which roles best match their resume using AI-based match scoring.

Today, candidates browse job boards manually and have no idea how well they actually fit a role until they apply and wait. HR teams get flooded with applications with no fast way to see who's actually a strong fit. This product closes that loop: every job a candidate sees is automatically scored against their resume, sorted best-fit-first, and every score comes with a plain-language explanation — not just a black-box number.

## 2. Goals

- Let HR create, edit, and close job postings with structured requirements (skills, experience, education, location, type).
- Let candidates register, upload a resume, and instantly see an AI-generated match score against every open job.
- Score computation must be **explainable** (a human-readable summary, not just a percentage) and **deterministic/offline** (no paid API dependency, must survive a live demo with flaky wifi).
- Ship a **live, deployed** product judges can access via URL — not a localhost-only demo.

## 3. Users / Personas

| Persona | Description | Key capabilities |
|---|---|---|
| **HR Admin** | Posts and manages roles, reviews applicants | Login, create job postings, edit/close postings, view applicants ranked by match |
| **Candidate / Employee** | Looking for their next role | Register, upload resume, search/filter jobs, see match % + explanation, apply |
| **AI Matching Engine** | System actor, not a human user | Parses resumes, compares against job requirements, computes weighted match score + explanation |

## 4. Functional Requirements

### 4.1 HR Features (must-have)
- HR login
- Create job postings
- Add role title
- Add responsibilities (free text — also feeds the AI role-relevance scoring)
- Add required experience (min–max years)
- Add required skills
- Add location
- Add job type (full-time / part-time / contract / internship)
- Edit or close postings
- View applicants — **sorted by match score, highest first**, with each applicant's score summary visible inline

### 4.2 Candidate Features (must-have)
- Register and login
- Upload resume (PDF or DOCX)
- Search jobs
- **Filters**: role, skill, location, experience — combinable with each other
- **Default sort: highest AI match % first** (also allow "newest" and "experience" as alternate sort options, but match-desc is the default on page load)
- View AI match percentage **and** a human-readable summary of *why* that's the score (e.g. which skills matched/are missing, whether experience meets the bar, education/cert fit, location fit)
- Apply to a job

### 4.3 AI Resume Match Features (must-have)
The AI engine compares, per the brief:
- Resume skills vs. job required skills
- Years of experience
- Previous project experience
- Education
- Certifications
- Role relevance (semantic similarity to responsibilities text)
- Keywords from job description

**Match Score Formula (fixed, as specified in the brief):**

| Component | Weight |
|---|---|
| Skills Match | 40% |
| Experience Match | 25% |
| Role Responsibility Match | 20% |
| Education/Certification Match | 10% |
| Location/Other Fit | 5% |

Each component is scored 0–100 independently, then combined by the weights above into a single 0–100 total. Full formula detail (how each sub-score is computed) is in `ARCHITECTURE.md` §4.

**Explainability requirement (added scope, beyond the base brief):** the AI must never surface a bare number alone. Every score is paired with a template-generated, plain-language breakdown, e.g.:

> "Skills: 8/10 matched, missing: Kubernetes, Terraform | Experience: 4.0 yrs vs required 3–5 ✓ | Role relevance: 71% similarity to responsibilities | Education: Bachelor's, relevant certification found | Location: exact → **Overall match: 78%**"

This is generated deterministically from the sub-scores (no LLM call needed), so it works fully offline and costs nothing.

## 5. Non-Functional Requirements

- **Offline-safe AI**: matching must not depend on a live internet connection or a paid API key at demo time (local embeddings model, baked into the deploy image).
- **Deployed, not local-only**: frontend + backend must be reachable via a public URL for judges.
- **Fast enough for a live demo**: resume parsing + scoring should complete in well under 2 seconds per resume/job pair.
- **Time-boxed**: must-have scope is designed to be shippable by a small team inside ~16 hours of build time, leaving a buffer for deployment and polish inside the 24-hour window.

## 6. Existing Platforms — Competitive Landscape

| Platform | Strength | Pricing model | Resume-match transparency | Candidate-facing match % |
|---|---|---|---|---|
| **Greenhouse** | Structured hiring, published bias audits, deep analytics | Enterprise (custom pricing) | Recruiter-facing scoring, not exposed to candidates | No |
| **Lever** | ATS + CRM, AI candidate recommendations, resume anonymization for diversity | Enterprise (custom pricing) | Internal ranking only | No |
| **SmartRecruiters** | Enterprise-scale parsing, global workflows, large integration marketplace | Enterprise (custom pricing) | Internal ranking only | No |
| **Manatal** | Affordable, AI candidate recommendations + social enrichment | $15–75/user/month | Internal scoring, limited candidate visibility | Partial |
| **Open-source academic tools** (SBERT/embedding resume-JD matchers, Streamlit ATS scorers) | Validate embedding + weighted-scoring approach as sound prior art | Free (DIY, not productized) | Varies, usually a raw score with no explanation | Sometimes, but no filters/sort UX around it |

**Where this project differentiates:**
1. **Candidate-facing, match-first UX** — mainstream ATS platforms compute match/fit scores for *recruiters*; candidates rarely see a transparent percentage at all. This product puts the match % and its explanation directly in front of the candidate, sorted best-fit-first by default.
2. **Explainable, not a black box** — every score ships with a plain-language breakdown of the five weighted components, not just a number.
3. **Free and offline-capable AI** — no per-seat enterprise pricing, no paid LLM API dependency; runs on local embeddings + rule-based extraction.
4. **Deterministic and auditable** — the fixed weighted formula (40/25/20/10/5) means HR can trust and explain *why* a candidate ranked where they did, unlike opaque proprietary ranking algorithms in enterprise ATS tools.

## 7. Success Criteria / Demo Scenario

End-to-end script judges should be able to see live:
1. HR Admin logs in, posts a job (e.g. "Backend Engineer," skills: Python, FastAPI, PostgreSQL; 3–5 yrs experience; Bengaluru).
2. Two seeded candidate accounts with different resumes (one strong fit, one weak fit) log in and search jobs.
3. Job list is sorted **highest match % first** by default; filters (skill/location/experience) narrow the list live.
4. Candidate clicks into the job, sees the full match breakdown/summary, and applies.
5. HR Admin views the applicants list for that job — sorted by match score, each with the same explanation shown to the candidate.

Success = this entire loop works on the **live deployed URL**, not just localhost.

## 8. Scope: MVP vs. Stretch

**In scope for MVP (must-ship, all of §4.1–4.3 above).**

**Stretch goals (only after MVP is fully working), ranked by effort:impact:**
1. Missing-skill highlighting as chips on the candidate job-search UI (near-free — data already computed)
2. HR shortlist/reject status on applicants
3. "Recommended for you" — proactive job recommendations on the candidate dashboard using the same scoring engine, no search required
4. Resume improvement tips generated from the missing-skills data
5. HR analytics dashboard (applicants per job, average match score, skill-gap trends)
6. Dark mode

## 9. Out of Scope (for this hackathon)

- Payment/billing, multi-tenant company accounts, SSO/OAuth login
- Real-time notifications/email
- Mobile app (responsive web only)
- Any paid LLM API integration (explicitly excluded per team decision — see §5)

---

*Full technical architecture, database schema, scoring algorithm implementation detail, API design, and the 24-hour build plan are in [`ARCHITECTURE.md`](./ARCHITECTURE.md).*
