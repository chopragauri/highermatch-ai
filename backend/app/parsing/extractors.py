"""
Resume field extraction, with two interchangeable engines.

Primary: an LLM parse (OpenCode Go / OpenAI-compatible) that reads the whole
resume at once and returns structured JSON. Handles unusual layouts that regex
can't.

Fallback: the deterministic rule-based parser in `rule_based.py`.

The fallback exists because the LLM path needs a network call and an API key,
and the previous version of this module returned EMPTY data on any failure —
which silently collapsed every match score (a 99% candidate scored 34%) while
still looking like it worked. Degrading to regex keeps scores meaningful with no
key, no network, or a provider outage, which is what preserves the project's
offline guarantee.

Both engines apply the same rule: internships/traineeships do not count as
professional experience.
"""
import json
import re
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from .. import config

from .rule_based import (  # noqa: F401 — re-exported so callers/tests keep working
    extract_certifications,
    extract_education,
    extract_experience_years,
    extract_project_keywords,
    extract_skills,
)

_LLM_TIMEOUT_SECONDS = 20.0


class Education(BaseModel):
    degree: Optional[str] = Field(
        default=None, description="The degree name, e.g. 'B.Tech', 'Master's', 'PhD'"
    )
    field: Optional[str] = Field(default=None, description="The field of study")
    institution: Optional[str] = Field(default=None, description="University or institution name")
    tier: int = Field(
        default=0, description="1 Diploma/School, 2 Bachelor's, 3 Master's, 4 PhD"
    )


class ResumeData(BaseModel):
    skills: List[str] = Field(default_factory=list, description="Technical skills and tools")
    experience_yrs: float = Field(
        default=0.0,
        description=(
            "Total years of PROFESSIONAL work experience. EXCLUDE internships, "
            "traineeships, apprenticeships and co-ops entirely — they are training, "
            "not professional tenure. Return 0 if every role was an internship."
        ),
    )
    education: List[Education] = Field(default_factory=list)
    certifications: List[str] = Field(
        default_factory=list,
        description="Named certifications only (e.g. 'AWS Certified Solutions Architect'). "
        "Do NOT return the bare words 'Certification' or 'Certified'.",
    )
    project_keywords: List[str] = Field(
        default_factory=list, description="Technical tools used specifically in projects"
    )


def _normalize_skills(skills: List[str]) -> List[str]:
    """
    Bring LLM skill output into the same shape the scorer compares against.

    Job postings store plain lowercase tokens ("postgresql"), but the LLM echoes the
    resume's own phrasing — "PostgreSQL/pgvector", "Java (Core)", "OOPs (Java)".
    score_skills() only lowercases before set-intersecting, so "postgresql/pgvector"
    never equals "postgresql" and the candidate silently loses credit for a skill they
    demonstrably have. Splitting on separators and dropping parenthetical qualifiers
    fixes the match without touching the scoring logic itself.
    """
    normalized: List[str] = []
    for raw in skills:
        if not raw or not raw.strip():
            continue
        # Drop trailing qualifiers: "Java (Core)" -> "Java"
        cleaned = re.sub(r"\([^)]*\)", " ", raw)
        # "PostgreSQL/pgvector" and "HTML, CSS" are each several skills
        for part in re.split(r"[/,;|]| and ", cleaned):
            token = part.strip().lower()
            if token and token not in normalized:
                normalized.append(token)
    return normalized


def _rule_based_parse(raw_text: str) -> ResumeData:
    """Deterministic parse — no network, no key, always available."""
    return ResumeData(
        skills=extract_skills(raw_text),
        experience_yrs=extract_experience_years(raw_text),
        education=[Education(**edu) for edu in extract_education(raw_text)],
        certifications=extract_certifications(raw_text),
        project_keywords=extract_project_keywords(raw_text),
    )


def _llm_parse(raw_text: str) -> Optional[ResumeData]:
    """Returns None (never raises, never returns empty-on-failure) so the caller
    can fall back to the deterministic parser instead of silently zeroing scores."""
    if not config.OPENCODE_API_KEY:
        return None

    try:
        client = OpenAI(
            api_key=config.OPENCODE_API_KEY,
            base_url=config.OPENCODE_BASE_URL,
            timeout=_LLM_TIMEOUT_SECONDS,
        )
        schema = ResumeData.model_json_schema()
        prompt = (
            "You are an expert HR parser. Extract the following information from the "
            "resume text. Output MUST be a valid JSON object exactly matching this "
            "JSON schema, and you MUST honour every field description — especially the "
            "rule that internships do not count toward years of experience.\n\n"
            f"{json.dumps(schema, indent=2)}\n\nResume Text:\n{raw_text}\n"
        )
        response = client.chat.completions.create(
            model=config.OPENCODE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You output structured JSON only. Never invent facts.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        # Some models wrap JSON in markdown fences even in json_object mode.
        content = re.sub(r"```(?:json)?\s*", "", content).strip()
        if not content:
            return None
        parsed = ResumeData(**json.loads(content))
        parsed.skills = _normalize_skills(parsed.skills)
        parsed.project_keywords = _normalize_skills(parsed.project_keywords)
        return parsed
    except Exception as exc:
        # Logged loudly rather than swallowed — an empty parse used to look identical
        # to a successful one, which made this failure mode invisible in the UI.
        print(f"[parsing] LLM parse failed ({exc}); falling back to rule-based parser.")
        return None


def extract_resume_data(raw_text: str) -> ResumeData:
    parsed = _llm_parse(raw_text)
    if parsed is not None and (parsed.skills or parsed.experience_yrs or parsed.education):
        return parsed
    # Covers both an unavailable LLM and one that returned a structurally valid but
    # empty result — either way, regex beats handing the scorer nothing.
    return _rule_based_parse(raw_text)
