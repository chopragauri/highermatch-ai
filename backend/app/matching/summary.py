"""
Deterministic, template-based human-readable match explanation.

No LLM call — this is pure string composition from the sub-score detail dicts
produced by scoring.py, so it's free, offline-safe, and instant. Compared to a
flat "Skills: x/y | Experience: ..." dump, this version leads with a verdict,
writes full sentences, and orders points by how much they matter to the score
(skills and experience first, since they carry 65% of the weight together).
"""

from typing import Any, Dict

# Skills whose conventional casing is an acronym, not a title-cased word — without
# this, "ai" .title()'s to "Ai" and "aws" to "Aws", which reads as a typo.
_ACRONYM_SKILLS = {
    "ai", "aws", "gcp", "sql", "css", "html", "api", "ui", "ux", "nlp", "llm",
    "mlops", "ci/cd", "etl", "a/b testing", "grpc", "ccna", "cka", "ckad",
}


def _label_skill(skill: str) -> str:
    return skill.upper() if skill.lower() in _ACRONYM_SKILLS else skill.title()


def _verdict(total: float) -> str:
    if total >= 85:
        return "Excellent match"
    if total >= 70:
        return "Strong match"
    if total >= 55:
        return "Good match"
    if total >= 40:
        return "Moderate match"
    return "Weak match"


def _skills_sentence(skills: Dict[str, Any]) -> str:
    required = skills["required_count"]
    matched = skills["matched_count"]
    if required == 0:
        return "No specific skills were required for this role."
    if not skills["missing"]:
        shown = ", ".join(_label_skill(s) for s in skills["matched"][:6])
        return f"All {required} required skills are covered ({shown})."

    matched_preview = ", ".join(_label_skill(s) for s in skills["matched"][:4]) if skills["matched"] else "none yet"
    missing_preview = ", ".join(_label_skill(s) for s in skills["missing"][:4])
    extra = " and others" if len(skills["missing"]) > 4 else ""
    return (
        f"Matches {matched}/{required} required skills ({matched_preview}); "
        f"missing {missing_preview}{extra}."
    )


def _experience_sentence(exp: Dict[str, Any]) -> str:
    years = exp["resume_years"]
    required_min = exp["required_min"]
    required_max = exp["required_max"]
    range_str = f"{required_min:g}–{required_max:g} yrs" if required_max else f"{required_min:g}+ yrs"

    if exp["verdict"] == "meets":
        return f"{years:g} years of experience fits the required range ({range_str})."
    if exp["verdict"] == "exceeds":
        return (
            f"{years:g} years of experience exceeds the required {range_str} — "
            "possibly overqualified, but not disqualifying."
        )
    return f"{years:g} years of experience falls short of the required {range_str}."


def _role_sentence(role: Dict[str, Any]) -> str:
    score = role["rescaled_score"]
    if score >= 70:
        return f"Resume content is highly relevant to the role's responsibilities ({score:.0f}% similarity)."
    if score >= 40:
        return f"Resume shows moderate alignment with the role's responsibilities ({score:.0f}% similarity)."
    return f"Resume content has limited overlap with the stated responsibilities ({score:.0f}% similarity)."


def _education_sentence(edu: Dict[str, Any]) -> str:
    degree = edu.get("highest_degree") or "no degree listed"
    parts = [f"Highest qualification: {degree}"]
    marks = []
    if edu.get("tenth_percentage") is not None:
        marks.append(f"class 10: {edu['tenth_percentage']:g}%")
    if edu.get("twelfth_percentage") is not None:
        marks.append(f"class 12: {edu['twelfth_percentage']:g}%")
    if marks:
        parts.append(" (" + ", ".join(marks) + ")")
    return "".join(parts) + "."


def _location_sentence(loc: Dict[str, Any]) -> str:
    mapping = {
        "remote": "This role is remote, so location isn't a constraint.",
        "exact": "Candidate's location matches the job location.",
        "none": "Candidate has no stated location preference on file.",
        "mismatch": f"Candidate's location differs from the job location ({loc['job_location']}).",
    }
    return mapping.get(loc["match_type"], "")


def generate_summary(
    skills: Dict[str, Any],
    exp: Dict[str, Any],
    role: Dict[str, Any],
    edu: Dict[str, Any],
    loc: Dict[str, Any],
    total: float,
) -> str:
    sentences = [
        f"{_verdict(total)} ({total:.0f}%).",
        _skills_sentence(skills),
        _experience_sentence(exp),
        _role_sentence(role),
        _education_sentence(edu),
        _location_sentence(loc),
    ]
    return " ".join(s for s in sentences if s)
