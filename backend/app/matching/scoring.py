"""
Weighted resume-to-job match scoring.

Weights are fixed by the hackathon brief and must not be changed without
updating PRD.md: Skills 40% / Experience 25% / Role Responsibility 20% /
Education+Certification 10% / Location 5%.
"""

from typing import Any, Dict, List, Optional, Tuple

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


EDU_TIER = {"phd": 4, "master": 3, "mba": 3, "bachelor": 2, "diploma": 1}


def _tier_of(label: Optional[str]) -> int:
    if not label:
        return 0
    label_lower = label.lower()
    for key, tier in EDU_TIER.items():
        if key in label_lower:
            return tier
    return 0


def score_education(
    parsed_education: List[Dict[str, Any]],
    certifications: List[str],
    required_education: Optional[str],
) -> Tuple[float, Dict[str, Any]]:
    highest_tier = 0
    highest_degree = None
    for edu in parsed_education or []:
        tier = edu.get("tier") or _tier_of(edu.get("degree"))
        if tier > highest_tier:
            highest_tier = tier
            highest_degree = edu.get("degree")

    required_tier = _tier_of(required_education)

    if required_tier == 0:
        base = 70.0 if highest_tier > 0 else 40.0
    elif highest_tier >= required_tier:
        base = 70.0
    else:
        base = 70.0 * (highest_tier / required_tier)

    has_cert = bool(certifications)
    score = min(100.0, base + (30.0 if has_cert else 0.0))

    return score, {
        "highest_degree": highest_degree,
        "required_degree": required_education,
        "has_relevant_cert": has_cert,
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


def compute_match(
    resume, job, candidate_location: Optional[str] = None, use_llm: bool = False
) -> Dict[str, Any]:
    """
    `resume` and `job` are SQLAlchemy model instances (models.Resume, models.JobPosting).
    Returns {"total": float, "breakdown": dict, "summary": str, "ai_generated": bool}.

    `use_llm=True` tries a Groq rewrite of the summary (falls back silently to the
    template version on any failure). Deliberately opt-in and off by default: the
    search endpoint calls compute_match once per open job per request, and firing an
    LLM call for every row of a search results page would be slow and wasteful. Only
    single-job call sites (the match-detail view, applying) pass use_llm=True.
    """
    skills_score, skills_detail = score_skills(resume.parsed_skills, job.required_skills)
    experience_score, exp_detail = score_experience(
        resume.parsed_experience_yrs, job.min_experience_yrs, job.max_experience_yrs
    )
    role_score, role_detail = score_role_responsibility(
        resume.resume_embedding, job.responsibilities_embedding
    )
    education_score, edu_detail = score_education(
        resume.parsed_education, resume.parsed_certifications, job.required_education
    )
    location_score, loc_detail = score_location(candidate_location, job.location)

    total = (
        skills_score * WEIGHTS["skills"]
        + experience_score * WEIGHTS["experience"]
        + role_score * WEIGHTS["role"]
        + education_score * WEIGHTS["education"]
        + location_score * WEIGHTS["location"]
    )
    total = round(total, 2)

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

    return {"total": total, "breakdown": breakdown, "summary": summary, "ai_generated": ai_generated}
