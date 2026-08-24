"""
Sanity tests for the matching engine — no DB required. Confirms sub-scores move
in the right direction and that a clearly-strong-fit resume outranks a
clearly-weak-fit one for the same job, which is the property the whole
"sort by match %" feature depends on.
"""
from types import SimpleNamespace

from datetime import date

from app.ages import check_age_eligibility
from app.matching.embeddings import embed_text
from app.matching.scoring import (
    compute_match,
    score_education,
    score_experience,
    score_location,
    score_skills,
)


def make_profile(**overrides):
    defaults = dict(
        education=[{"degree": "B.Tech", "tier": 2}],
        tenth_percentage=90.0,
        twelfth_percentage=90.0,
        preferred_location="Bengaluru",
        current_location="Bengaluru",
        date_of_birth=date(1998, 1, 1),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_job(**overrides):
    defaults = dict(
        required_skills=["python", "fastapi", "postgresql", "docker"],
        min_experience_yrs=3,
        max_experience_yrs=6,
        required_education="Bachelor's",
        location="Bengaluru",
        min_age=None,
        max_age=None,
        responsibilities="Design and build scalable REST APIs using Python and FastAPI.",
    )
    defaults.update(overrides)
    defaults["responsibilities_embedding"] = embed_text(defaults["responsibilities"])
    return SimpleNamespace(**defaults)


def make_resume(**overrides):
    defaults = dict(
        parsed_skills=["python", "fastapi", "postgresql", "docker", "aws"],
        parsed_experience_yrs=4,
        parsed_education=[{"degree": "B.Tech", "tier": 2}],
        parsed_certifications=["AWS Certified"],
        raw_text="Backend engineer building REST APIs with Python and FastAPI.",
    )
    defaults.update(overrides)
    defaults["resume_embedding"] = embed_text(defaults["raw_text"])
    return SimpleNamespace(**defaults)


def test_skills_score_exact_match():
    score, detail = score_skills(["python", "fastapi"], ["python", "fastapi"])
    assert score == 100.0
    assert detail["missing"] == []


def test_skills_score_partial_match():
    score, detail = score_skills(["python"], ["python", "fastapi", "docker"])
    assert 0 < score < 100
    assert "fastapi" in detail["missing"] and "docker" in detail["missing"]


def test_skills_score_no_required_skills_is_full_score():
    score, _ = score_skills(["python"], [])
    assert score == 100.0


def test_experience_score_meets_range():
    score, detail = score_experience(4, 3, 6)
    assert score == 100.0
    assert detail["verdict"] == "meets"


def test_experience_score_below_range_is_penalized():
    score, detail = score_experience(1, 3, 6)
    assert score < 100.0
    assert detail["verdict"] == "below"


def test_experience_score_overqualified_only_mild_penalty():
    score, detail = score_experience(15, 3, 6)
    assert 80.0 <= score < 100.0
    assert detail["verdict"] == "exceeds"


def test_education_score_uses_profile_marks_not_resume():
    high, _ = score_education([{"degree": "B.Tech", "tier": 2}], 95.0, 95.0, "Bachelor's")
    low, _ = score_education([{"degree": "B.Tech", "tier": 2}], 50.0, 50.0, "Bachelor's")
    assert high > low


def test_education_score_penalizes_insufficient_degree():
    meets, _ = score_education([{"degree": "Master's", "tier": 3}], 90.0, 90.0, "Master's")
    below, _ = score_education([{"degree": "Diploma", "tier": 1}], 90.0, 90.0, "Master's")
    assert meets > below


def test_location_score_remote_always_full():
    score, detail = score_location("Chennai", "Remote")
    assert score == 100.0
    assert detail["match_type"] == "remote"


def test_location_score_mismatch_is_low_but_not_zero():
    score, _ = score_location("Chennai", "Bengaluru")
    assert 0 < score < 60


def test_strong_fit_outranks_weak_fit_for_same_job():
    job = make_job()

    strong_resume = make_resume()
    weak_resume = make_resume(
        parsed_skills=["digital marketing", "seo", "excel"],
        parsed_experience_yrs=5,
        parsed_education=[{"degree": "Bachelor's", "tier": 2}],
        parsed_certifications=[],
        raw_text="Marketing specialist running SEO and content campaigns.",
    )

    strong_match = compute_match(strong_resume, job, make_profile())
    weak_match = compute_match(weak_resume, job, make_profile())

    assert strong_match["total"] > weak_match["total"]
    assert strong_match["total"] >= 70  # strong fit should read as "Strong match" or better
    assert "Weak match" in weak_match["summary"] or "Moderate match" in weak_match["summary"]


def test_summary_is_not_a_bare_number():
    job = make_job()
    resume = make_resume()
    match = compute_match(resume, job, make_profile())
    assert len(match["summary"]) > 40
    assert "%" in match["summary"]
    assert match["summary"] != str(match["total"])


def test_llm_disabled_by_default_uses_template_summary():
    """compute_match must not call the LLM unless explicitly asked — the search
    endpoint scores every open job per request and can't afford a call per row."""
    job = make_job()
    resume = make_resume()
    match = compute_match(resume, job, make_profile())
    assert match["ai_generated"] is False
    assert "Excellent match" in match["summary"] or "Strong match" in match["summary"]


def test_llm_failure_falls_back_to_template_summary(monkeypatch):
    """A Groq outage/rate-limit/timeout must degrade to the local summary, never
    raise — this is what keeps the app usable fully offline."""
    import app.matching.scoring as scoring_module

    def boom(*args, **kwargs):
        raise RuntimeError("simulated Groq outage")

    monkeypatch.setattr(scoring_module, "generate_llm_summary", boom)

    job = make_job()
    resume = make_resume()
    try:
        match = compute_match(resume, job, make_profile(), use_llm=True)
    except RuntimeError:
        raise AssertionError("compute_match must not propagate LLM errors")

    assert match["ai_generated"] is False
    assert len(match["summary"]) > 40


def test_internships_are_not_counted_as_experience():
    """A resume whose only roles are internships must read as 0 years."""
    from app.parsing.extractors import extract_experience_years

    text = (
        "Experience\n"
        "AcmeCorp May 2023 - Aug 2023\n"
        "Software Engineering Intern Remote\n"
        "- Built things\n"
        "Education\n"
        "B.Tech 2020 - 2024\n"
    )
    assert extract_experience_years(text) == 0.0


def test_full_time_role_still_counts_as_experience():
    from app.parsing.extractors import extract_experience_years

    text = (
        "Experience\n"
        "AcmeCorp Jan 2020 - Jan 2024\n"
        "Senior Engineer Remote\n"
        "Education\n"
        "B.Tech 2014 - 2018\n"
    )
    assert extract_experience_years(text) == 4.0


def test_age_eligibility_blocks_out_of_range_candidates():
    too_young = date.today().replace(year=date.today().year - 17)
    ok, reason = check_age_eligibility(too_young, 21, None)
    assert ok is False and "21" in reason

    eligible = date.today().replace(year=date.today().year - 30)
    ok, reason = check_age_eligibility(eligible, 21, 40)
    assert ok is True and reason is None


def test_job_without_age_criteria_accepts_everyone():
    ok, reason = check_age_eligibility(None, None, None)
    assert ok is True and reason is None


def test_missing_dob_is_ineligible_when_job_sets_criteria():
    ok, reason = check_age_eligibility(None, 21, None)
    assert ok is False and reason


def test_match_reports_age_ineligibility():
    job = make_job(min_age=40)
    resume = make_resume()
    match = compute_match(resume, job, make_profile(date_of_birth=date(2005, 1, 1)))
    assert match["age_eligible"] is False
    assert "40" in match["age_ineligible_reason"]


def test_parser_falls_back_to_rules_when_llm_unavailable(monkeypatch):
    """The LLM parser must never hand the scorer empty data. A previous version
    returned skills=[]/experience=0 on any failure, which silently dropped a 99%
    candidate to 34% while still looking like a successful parse."""
    from app.parsing import extractors

    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)

    parsed = extractors.extract_resume_data(
        "Backend Engineer\n"
        "Skills: Python, FastAPI, PostgreSQL, Docker\n"
        "Experience\n"
        "TechCorp 2020 - 2024\n"
        "Senior Backend Engineer\n"
    )
    assert parsed.skills, "fallback must still extract skills"
    assert parsed.experience_yrs == 4.0


def test_parser_falls_back_when_llm_returns_empty(monkeypatch):
    """A structurally valid but empty LLM response is treated as a failure too."""
    from app.parsing import extractors

    monkeypatch.setattr(extractors, "_llm_parse", lambda _text: extractors.ResumeData())

    parsed = extractors.extract_resume_data(
        "Skills: Python, Docker\nExperience\nAcme 2019 - 2023\nEngineer\n"
    )
    assert parsed.skills
    assert parsed.experience_yrs == 4.0
