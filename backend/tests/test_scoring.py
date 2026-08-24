"""
Sanity tests for the matching engine — no DB required. Confirms sub-scores move
in the right direction and that a clearly-strong-fit resume outranks a
clearly-weak-fit one for the same job, which is the property the whole
"sort by match %" feature depends on.
"""
from types import SimpleNamespace

from app.matching.embeddings import embed_text
from app.matching.scoring import (
    compute_match,
    score_education,
    score_experience,
    score_location,
    score_skills,
)


def make_job(**overrides):
    defaults = dict(
        required_skills=["python", "fastapi", "postgresql", "docker"],
        min_experience_yrs=3,
        max_experience_yrs=6,
        required_education="Bachelor's",
        location="Bengaluru",
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


def test_education_score_rewards_certification():
    with_cert, _ = score_education([{"degree": "B.Tech", "tier": 2}], ["AWS Certified"], "Bachelor's")
    without_cert, _ = score_education([{"degree": "B.Tech", "tier": 2}], [], "Bachelor's")
    assert with_cert > without_cert


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

    strong_match = compute_match(strong_resume, job, candidate_location="Bengaluru")
    weak_match = compute_match(weak_resume, job, candidate_location="Bengaluru")

    assert strong_match["total"] > weak_match["total"]
    assert strong_match["total"] >= 70  # strong fit should read as "Strong match" or better
    assert "Weak match" in weak_match["summary"] or "Moderate match" in weak_match["summary"]


def test_summary_is_not_a_bare_number():
    job = make_job()
    resume = make_resume()
    match = compute_match(resume, job, candidate_location="Bengaluru")
    assert len(match["summary"]) > 40
    assert "%" in match["summary"]
    assert match["summary"] != str(match["total"])


def test_llm_disabled_by_default_uses_template_summary():
    """compute_match must not call the LLM unless explicitly asked — the search
    endpoint scores every open job per request and can't afford a call per row."""
    job = make_job()
    resume = make_resume()
    match = compute_match(resume, job, candidate_location="Bengaluru")
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
        match = compute_match(resume, job, candidate_location="Bengaluru", use_llm=True)
    except RuntimeError:
        raise AssertionError("compute_match must not propagate LLM errors")

    assert match["ai_generated"] is False
    assert len(match["summary"]) > 40
