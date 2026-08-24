"""
Optional Groq-powered rewrite of the deterministic match summary into a more
natural, readable explanation. This never computes or changes any score — the
weighted formula in scoring.py stays the sole source of truth for the numbers.
It only rewrites the sentence that explains them.

Fully optional and fail-safe: if GROQ_API_KEY is unset, the client can't be
built, the network is unreachable, or the call errors or times out, callers get
None back and fall back to the local template summary from summary.py. The app
never depends on this being available.
"""
from functools import lru_cache
from typing import Any, Dict, Optional

from .. import config

_TIMEOUT_SECONDS = 6.0

# Generous relative to the ~60-token answer we want: gpt-oss models spend tokens on
# internal reasoning before emitting content, and a tight cap truncates the response
# to an empty string rather than erroring.
_MAX_TOKENS = 400


@lru_cache(maxsize=1)
def _get_client():
    if not config.GROQ_API_KEY:
        return None
    try:
        from groq import Groq

        return Groq(api_key=config.GROQ_API_KEY, timeout=_TIMEOUT_SECONDS)
    except Exception:
        return None


def _build_prompt(
    skills: Dict[str, Any],
    exp: Dict[str, Any],
    role: Dict[str, Any],
    edu: Dict[str, Any],
    loc: Dict[str, Any],
    total: float,
) -> str:
    range_str = (
        f"{exp['required_min']:g}-{exp['required_max']:g} yrs"
        if exp.get("required_max")
        else f"{exp['required_min']:g}+ yrs"
    )
    return (
        "Rewrite this job-match result as a natural, honest 2-3 sentence explanation "
        "for a candidate. Do not invent facts or change any numbers — only rephrase "
        "the ones given. Do not use markdown. Keep it concise.\n\n"
        f"Overall match: {total:.0f}%\n"
        f"Skills: {skills['matched_count']}/{skills['required_count']} required skills matched"
        + (f"; missing: {', '.join(skills['missing'])}" if skills["missing"] else "")
        + "\n"
        f"Experience: candidate has {exp['resume_years']:g} yrs, role requires {range_str} "
        f"(verdict: {exp['verdict']})\n"
        f"Role relevance: {role['rescaled_score']:.0f}% semantic similarity to the job "
        "responsibilities\n"
        f"Education: highest degree is {edu['highest_degree'] or 'not listed'}"
        + (", has a relevant certification" if edu["has_relevant_cert"] else "")
        + "\n"
        f"Location fit: {loc['match_type']}\n"
    )


def generate_llm_summary(
    skills: Dict[str, Any],
    exp: Dict[str, Any],
    role: Dict[str, Any],
    edu: Dict[str, Any],
    loc: Dict[str, Any],
    total: float,
) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain job-match scores factually and concisely. Never "
                        "invent numbers or facts not given to you."
                    ),
                },
                {"role": "user", "content": _build_prompt(skills, exp, role, edu, loc, total)},
            ],
            temperature=0.4,
            max_tokens=_MAX_TOKENS,
            timeout=_TIMEOUT_SECONDS,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        # Network error, rate limit, timeout, malformed response — any failure here
        # silently falls back to the deterministic summary. This must never raise
        # into compute_match(), since matching has to keep working without Groq.
        return None
