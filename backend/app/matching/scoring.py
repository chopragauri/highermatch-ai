"""
Weighted resume-to-job match scoring.

Weights are fixed by the hackathon brief and must not be changed without
updating PRD.md: Skills 40% / Experience 25% / Role Responsibility 20% /
Education+Certification 10% / Location 5%.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..ages import check_age_eligibility
from .embeddings import cosine_similarity, get_model
from .llm_summary import generate_llm_summary
from .summary import generate_summary

WEIGHTS = {
    "skills": 0.40,
    "experience": 0.25,
    "role": 0.20,
    "education": 0.10,
    "location": 0.05,
}

SKILL_SYNONYM_THRESHOLD = 0.75


def score_skills(
    resume_skills: List[str], required_skills: List[str]
) -> Tuple[float, Dict[str, Any]]:
    resume_set = {s.lower().strip() for s in resume_skills if s.strip()}
    required_set = {s.lower().strip() for s in required_skills if s.strip()}

    if not required_set:
        return 100.0, {"matched": [], "missing": [], "matched_count": 0, "required_count": 0}

    matched = required_set & resume_set
    unmatched_required = required_set - matched
    unmatched_resume = resume_set - matched

    # Semantic fallback for synonyms the taxonomy didn't catch verbatim, e.g. resume
    # says "JS" and the job wants "JavaScript", or "Postgres" vs "PostgreSQL". Only run
    # on the leftover unmatched sets so this stays cheap.
    if unmatched_required and unmatched_resume:
        model = get_model()
        req_list = sorted(unmatched_required)
        res_list = sorted(unmatched_resume)
        req_emb = model.encode(req_list, convert_to_numpy=True)
        res_emb = model.encode(res_list, convert_to_numpy=True)
        for i, req_skill in enumerate(req_list):
            sims = [cosine_similarity(req_emb[i], res_emb[j]) for j in range(len(res_list))]
            if sims and max(sims) >= SKILL_SYNONYM_THRESHOLD:
                matched.add(req_skill)

    matched_count = len(matched)
    required_count = len(required_set)
    score = 100.0 * matched_count / required_count if required_count else 100.0
    missing = sorted(required_set - matched)
    return score, {
        "matched": sorted(matched),
        "missing": missing,
        "matched_count": matched_count,
        "required_count": required_count,
    }


def score_experience(
    resume_years: Optional[float], min_years: float, max_years: Optional[float]
) -> Tuple[float, Dict[str, Any]]:
    resume_years = float(resume_years or 0.0)
    min_years = float(min_years or 0.0)
    max_years = float(max_years) if max_years is not None else None

    if resume_years >= min_years and (max_years is None or resume_years <= max_years):
        verdict = "meets"
        score = 100.0
    elif resume_years < min_years:
        verdict = "below"
        score = 100.0 * max(0.0, resume_years / min_years) if min_years > 0 else 100.0
    else:
        verdict = "exceeds"
        over = resume_years - (max_years or resume_years)
        score = max(80.0, 100.0 - min(20.0, over * 5))

    return score, {
        "resume_years": resume_years,
        "required_min": min_years,
        "required_max": max_years,
        "verdict": verdict,
    }


def score_role_responsibility(
    resume_embedding, responsibilities_embedding
) -> Tuple[float, Dict[str, Any]]:
    if resume_embedding is None or responsibilities_embedding is None:
        return 0.0, {"cosine_similarity": 0.0, "rescaled_score": 0.0}
    cos_sim = cosine_similarity(resume_embedding, responsibilities_embedding)
    # Real-text cosine similarity from MiniLM realistically lands in ~[0.2, 0.7] for
    # related-but-imperfect matches, so a raw min-max rescale over that band makes the
    # 0-100 output actually spread out instead of clustering around 40-60.
    rescaled = 100.0 * min(1.0, max(0.0, (cos_sim - 0.2) / (0.7 - 0.2)))
    return rescaled, {"cosine_similarity": round(float(cos_sim), 4), "rescaled_score": rescaled}


# Degree -> tier. Must cover every option in the frontend's DEGREE_OPTIONS dropdown
# (lib/degrees.ts), since education is now sourced from the profile where the degree
# is chosen from that exact list. A looser map that only knew "bachelor"/"master"
# silently scored "B.Tech" as no-degree-at-all.
EDU_TIER_EXACT = {
    "diploma": 1,
    "bachelor's": 2, "bachelors": 2, "bachelor": 2,
    "b.tech": 2, "btech": 2, "b.e.": 2, "be": 2, "b.sc": 2, "bsc": 2,
    "bca": 2, "bba": 2, "b.com": 2, "bcom": 2, "b.a.": 2, "ba": 2,
    "master's": 3, "masters": 3, "master": 3,
    "m.tech": 3, "mtech": 3, "m.e.": 3, "me": 3, "m.sc": 3, "msc": 3,
    "mca": 3, "mba": 3, "m.com": 3, "mcom": 3, "m.a.": 3, "ma": 3,
    "phd": 4, "ph.d": 4, "ph.d.": 4, "doctorate": 4,
}

# Fallback substring probes, longest-first so "m.tech" wins before a bare "tech"
# and "master" before "ma". Only consulted when the exact lookup misses.
EDU_TIER_CONTAINS = [
    ("doctorate", 4), ("phd", 4), ("ph.d", 4),
    ("m.tech", 3), ("mtech", 3), ("m.sc", 3), ("msc", 3), ("mba", 3),
    ("mca", 3), ("master", 3),
    ("b.tech", 2), ("btech", 2), ("b.sc", 2), ("bsc", 2), ("bca", 2),
    ("bba", 2), ("bachelor", 2),
    ("diploma", 1),
]

# Kept as an alias so any external reference to the old name still resolves.
EDU_TIER = EDU_TIER_EXACT


def _tier_of(label: Optional[str]) -> int:
    if not label:
        return 0
    normalized = label.strip().lower()
    if normalized in EDU_TIER_EXACT:
        return EDU_TIER_EXACT[normalized]
    for key, tier in EDU_TIER_CONTAINS:
        if key in normalized:
            return tier
    return 0


def score_education(
    profile_education: List[Dict[str, Any]],
    tenth_percentage: Optional[float],
    twelfth_percentage: Optional[float],
    required_education: Optional[str],
) -> Tuple[float, Dict[str, Any]]:
    """
    Education is sourced ENTIRELY from the candidate's registration profile — never
    from the resume. Structured self-declared data (a chosen degree, a numeric
    percentage) is far more reliable than regex-guessing a degree out of PDF text,
    and keeping a single source per sub-score is what prevents the two from
    disagreeing about the same candidate.

    Breakdown of the 100 points: degree tier 60, class 10 pct 20, class 12 pct 20.
    """
    highest_tier = 0
    highest_degree = None
    for edu in profile_education or []:
        tier = edu.get("tier") or _tier_of(edu.get("degree"))
        if tier > highest_tier:
            highest_tier = tier
            highest_degree = edu.get("degree")

    required_tier = _tier_of(required_education)
    if required_tier == 0:
        degree_points = 60.0 if highest_tier > 0 else 30.0
    elif highest_tier >= required_tier:
        degree_points = 60.0
    else:
        degree_points = 60.0 * (highest_tier / required_tier)

    tenth = float(tenth_percentage) if tenth_percentage is not None else None
    twelfth = float(twelfth_percentage) if twelfth_percentage is not None else None
    tenth_points = (tenth / 100.0) * 20.0 if tenth is not None else 0.0
    twelfth_points = (twelfth / 100.0) * 20.0 if twelfth is not None else 0.0

    score = min(100.0, degree_points + tenth_points + twelfth_points)

    return score, {
        "highest_degree": highest_degree,
        "required_degree": required_education,
        "tenth_percentage": tenth,
        "twelfth_percentage": twelfth,
        # Retained so existing summary/UI code that reads this key keeps working;
        # certifications are still parsed from the resume for display, but they no
        # longer feed the score (that would re-mix resume data into a profile-sourced
        # sub-score, which is exactly the overlap we are eliminating).
        "has_relevant_cert": False,
    }


def score_location(
    candidate_location: Optional[str], job_location: str
) -> Tuple[float, Dict[str, Any]]:
    job_location_norm = (job_location or "").strip().lower()

    if job_location_norm == "remote":
        return 100.0, {
            "job_location": job_location,
            "candidate_location": candidate_location,
            "match_type": "remote",
        }
    if not candidate_location:
        return 60.0, {
            "job_location": job_location,
            "candidate_location": candidate_location,
            "match_type": "none",
        }
    if candidate_location.strip().lower() == job_location_norm:
        return 100.0, {
            "job_location": job_location,
            "candidate_location": candidate_location,
            "match_type": "exact",
        }
    return 20.0, {
        "job_location": job_location,
        "candidate_location": candidate_location,
        "match_type": "mismatch",
    }


def compute_match(resume, job, profile=None, use_llm: bool = False) -> Dict[str, Any]:
    """
    `resume`, `job`, `profile` are model instances (Resume, JobPosting, CandidateProfile).

    Each sub-score has exactly ONE source, deliberately — no field is ever read from
    both the resume and the profile, so the two can never disagree about a candidate:

      Skills (40%)     <- resume only  (parsed_skills)
      Experience (25%) <- resume only  (parsed_experience_yrs, internships excluded)
      Role match (20%) <- resume only  (embedding vs job responsibilities)
      Education (10%)  <- profile only (degree, class 10 %, class 12 %)
      Location (5%)    <- profile only (preferred, falling back to current)

    Age eligibility is returned alongside the score but is NOT one of the weighted
    components — it is a hard gate enforced at apply time (see routers/applications).
    """
    skills_score, skills_detail = score_skills(resume.parsed_skills, job.required_skills)
    experience_score, exp_detail = score_experience(
        resume.parsed_experience_yrs, job.min_experience_yrs, job.max_experience_yrs
    )
    role_score, role_detail = score_role_responsibility(
        resume.resume_embedding, job.responsibilities_embedding
    )

    profile_education = getattr(profile, "education", None) or []
    education_score, edu_detail = score_education(
        profile_education,
        getattr(profile, "tenth_percentage", None),
        getattr(profile, "twelfth_percentage", None),
        job.required_education,
    )

    candidate_location = None
    if profile is not None:
        candidate_location = profile.preferred_location or profile.current_location
    location_score, loc_detail = score_location(candidate_location, job.location)

    total = (
        skills_score * WEIGHTS["skills"]
        + experience_score * WEIGHTS["experience"]
        + role_score * WEIGHTS["role"]
        + education_score * WEIGHTS["education"]
        + location_score * WEIGHTS["location"]
    )
    total = round(total, 2)

    age_eligible, age_reason = check_age_eligibility(
        getattr(profile, "date_of_birth", None), job.min_age, job.max_age
    )

    summary = generate_summary(skills_detail, exp_detail, role_detail, edu_detail, loc_detail, total)

    ai_generated = False
    if use_llm:
        # Belt-and-braces: generate_llm_summary already swallows its own failures,
        # but the guarantee that scoring never breaks because of the LLM is enforced
        # here too, at the boundary, so it holds no matter how that module changes.
        try:
            llm_text = generate_llm_summary(
                skills_detail, exp_detail, role_detail, edu_detail, loc_detail, total
            )
        except Exception:
            llm_text = None
        if llm_text:
            summary = llm_text
            ai_generated = True

    breakdown = {
        "skills": {"score": round(skills_score, 2), **skills_detail},
        "experience": {"score": round(experience_score, 2), **exp_detail},
        "role_responsibility": {"score": round(role_score, 2), **role_detail},
        "education": {"score": round(education_score, 2), **edu_detail},
        "location": {"score": round(location_score, 2), **loc_detail},
        "weights": WEIGHTS,
    }

    return {
        "total": total,
        "breakdown": breakdown,
        "summary": summary,
        "ai_generated": ai_generated,
        "age_eligible": age_eligible,
        "age_ineligible_reason": age_reason,
    }
