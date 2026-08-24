import datetime
import re
from typing import Any, Dict, List

from .skills_taxonomy import SKILLS_TAXONOMY

_SKILL_PATTERNS = [
    (skill, re.compile(r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"))
    for skill in SKILLS_TAXONOMY
]


def extract_skills(raw_text: str) -> List[str]:
    text_lower = (raw_text or "").lower()
    found = {skill for skill, pattern in _SKILL_PATTERNS if pattern.search(text_lower)}
    return sorted(found)


_EXPLICIT_EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of)?\s*experience", re.IGNORECASE)

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_PATTERN = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))

# Matches both "2020-2024" (bare years) and "May 2026 – Aug 2026" (month-year on
# either or both sides) — real resumes overwhelmingly use the latter, and a bare-year
# regex silently extracts zero experience from them.
_DATE_RANGE_RE = re.compile(
    rf"(?:(?P<start_month>{_MONTH_PATTERN})\.?\s+)?(?P<start_year>(?:19|20)\d{{2}})"
    rf"\s*[-–—]{{1,3}}\s*"
    rf"(?:(?P<end_month>{_MONTH_PATTERN})\.?\s+)?(?P<end_year>(?:19|20)\d{{2}}|present|current)",
    re.IGNORECASE,
)

# Section headers recognized as the start/end of a work-experience block. A line
# qualifies if it IS the header (standalone header line, typical of real resumes:
# "Experience" alone on its own line) OR STARTS WITH "header:" (inline label-and-
# content on one line, e.g. "Work Experience: Backend Engineer at TechCorp, ..."—
# common in tools/templates that flatten resumes into label:value lines). A plain
# substring search would also match "...two completed engineering internships." in
# a Summary paragraph; requiring the header at the START of the line avoids that.
_WORK_SECTION_HEADERS = [
    "work experience", "professional experience", "experience",
    "internships", "internship experience", "employment history",
]
_NEXT_SECTION_HEADERS = [
    "education", "certifications", "certification", "projects", "skills",
    "technical skills", "achievements", "achievements & certifications",
    "publications", "awards",
]


def _line_matches_header(line: str, headers: List[str]) -> bool:
    stripped = line.strip().lower()
    return any(stripped == h or stripped.startswith(h + ":") for h in headers)


def _work_experience_section(text: str) -> str:
    lines = text.split("\n")

    start_idx = None
    start_line_remainder = ""
    for i, line in enumerate(lines):
        if _line_matches_header(line, _WORK_SECTION_HEADERS):
            start_idx = i
            stripped = line.strip()
            colon_idx = stripped.find(":")
            start_line_remainder = stripped[colon_idx + 1 :] if colon_idx != -1 else ""
            break

    if start_idx is None:
        # No identifiable section heading — fall back to the whole resume, which
        # may slightly overcount if education date ranges are also present.
        return text

    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if _line_matches_header(lines[j], _NEXT_SECTION_HEADERS):
            end_idx = j
            break

    section_lines = [start_line_remainder] + lines[start_idx + 1 : end_idx]
    return "\n".join(section_lines)


def _month_index(month_str: Any, default: int = 6) -> int:
    if not month_str:
        return default
    return _MONTHS.get(month_str.lower(), default)


# Roles matching these are excluded from the experience total — an internship is
# training, not professional tenure, and counting it inflates a fresher's years.
_INTERNSHIP_MARKERS = ("intern", "internship", "trainee", "apprentice", "co-op")

# How many lines after a date range to scan for the role title. Resumes commonly put
# the company+dates on one line and the job title on the next, so the "Intern" marker
# sits below the date it belongs to rather than on the same line.
_ROLE_CONTEXT_LINES = 2


def _range_is_internship(work_lines: list, line_index: int) -> bool:
    window = work_lines[line_index : line_index + 1 + _ROLE_CONTEXT_LINES]
    blob = " ".join(window).lower()
    return any(marker in blob for marker in _INTERNSHIP_MARKERS)


def extract_experience_years(raw_text: str) -> float:
    """
    Total professional experience in years, parsed ONLY from this resume's own text.
    Internship/trainee roles are deliberately excluded.
    """
    raw_text = raw_text or ""
    now = datetime.datetime.now()
    work_section = _work_experience_section(raw_text)
    work_lines = work_section.split("\n")

    total_months = 0
    for line_index, line in enumerate(work_lines):
        if _range_is_internship(work_lines, line_index):
            continue
        for m in _DATE_RANGE_RE.finditer(line):
            start_year = int(m.group("start_year"))
            start_month = _month_index(m.group("start_month"))
            end_raw = m.group("end_year")
            if end_raw.lower() in ("present", "current"):
                end_year, end_month = now.year, now.month
            else:
                end_year = int(end_raw)
                # Same default (June) as the start month — an asymmetric default here
                # (e.g. December) would silently add 6 phantom months to every bare
                # "2020-2024"-style range with no month info on either side.
                end_month = _month_index(m.group("end_month"))

            months = (end_year - start_year) * 12 + (end_month - start_month)
            if months > 0:
                total_months += months

    ranges_total = round(total_months / 12, 1)

    # An explicit "N years of experience" claim is only trusted when it does not
    # contradict the dated roles we could actually verify. Taking an unconditional
    # max() let a summary line like "two completed internships ... 3 years experience"
    # reintroduce exactly the internship time the date scan just excluded.
    explicit = [float(m) for m in _EXPLICIT_EXP_RE.findall(raw_text)]
    if explicit and total_months == 0 and not _mentions_internship(raw_text):
        return round(max(explicit), 1)

    return ranges_total


def _mentions_internship(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _INTERNSHIP_MARKERS)


_DEGREE_KEYWORDS = [
    ("phd", "PhD", 4),
    ("ph.d", "PhD", 4),
    ("doctorate", "PhD", 4),
    ("m.tech", "M.Tech", 3),
    ("mtech", "M.Tech", 3),
    ("m.e.", "Master's", 3),
    ("m.s.", "Master's", 3),
    ("mba", "MBA", 3),
    ("master", "Master's", 3),
    ("b.tech", "B.Tech", 2),
    ("btech", "B.Tech", 2),
    ("b.e.", "Bachelor's", 2),
    ("b.s.", "Bachelor's", 2),
    ("bsc", "Bachelor's", 2),
    ("b.sc", "Bachelor's", 2),
    ("bachelor", "Bachelor's", 2),
    ("diploma", "Diploma", 1),
]


def extract_education(raw_text: str) -> List[Dict[str, Any]]:
    text_lower = (raw_text or "").lower()
    found: List[Dict[str, Any]] = []
    seen_tiers = set()
    for keyword, label, tier in _DEGREE_KEYWORDS:
        if keyword in text_lower and tier not in seen_tiers:
            found.append({"degree": label, "field": None, "institution": None, "tier": tier})
            seen_tiers.add(tier)
    return found


# (keyword to search for, correctly-cased display label). Deliberately does NOT
# include the bare words "certified"/"certification"/"certificate" — matching those
# alone just means the resume has a "Certifications" section header, not that it names
# an actual credential, and it was producing junk chips like "Certification" itself.
# Longer/more specific patterns are listed before their shorter substrings so the
# specific label wins (e.g. "aws certified solutions architect" before "aws certified").
_CERT_PATTERNS = [
    ("aws certified solutions architect", "AWS Certified Solutions Architect"),
    ("aws certified developer", "AWS Certified Developer"),
    ("aws certified", "AWS Certified"),
    ("microsoft certified", "Microsoft Certified"),
    ("azure certified", "Azure Certified"),
    ("google cloud certified", "Google Cloud Certified"),
    ("google data analytics", "Google Data Analytics Certificate"),
    ("ibm certified", "IBM Certified"),
    ("pmp", "PMP"),
    ("cissp", "CISSP"),
    ("certified scrum master", "Certified Scrum Master"),
    ("scrum master", "Scrum Master"),
    ("csm", "CSM"),
    ("six sigma", "Six Sigma"),
    ("comptia", "CompTIA"),
    ("ccna", "CCNA"),
    ("ckad", "CKAD"),
    ("cka", "CKA"),
    ("nptel", "NPTEL"),
    ("tensorflow developer certificate", "TensorFlow Developer Certificate"),
    ("deep learning specialization", "Deep Learning Specialization"),
    ("machine learning specialization", "Machine Learning Specialization"),
    ("data science professional certificate", "Data Science Professional Certificate"),
    ("hackerrank certified", "HackerRank Certified"),
]


def extract_certifications(raw_text: str) -> List[str]:
    text_lower = (raw_text or "").lower()
    found: List[str] = []
    matched_spans: List[str] = []
    for keyword, label in _CERT_PATTERNS:
        if keyword in text_lower and not any(keyword in span for span in matched_spans):
            found.append(label)
            matched_spans.append(keyword)
    return sorted(set(found))


_PROJECTS_SECTION_RE = re.compile(r"projects?([\s\S]{0,1500})", re.IGNORECASE)


def extract_project_keywords(raw_text: str) -> List[str]:
    # Feeds the role-relevance signal, not its own scoring weight, so this stays cheap:
    # reuse the skills taxonomy scan but scoped to a detected "Projects" section.
    match = _PROJECTS_SECTION_RE.search(raw_text or "")
    section = match.group(1) if match else raw_text
    return extract_skills(section)
