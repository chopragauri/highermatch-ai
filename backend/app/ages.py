"""
Age helpers, kept in one place so the eligibility rule can't drift between
validation (schemas.py), scoring (matching/scoring.py) and enforcement
(routers/applications.py).
"""
from datetime import date
from typing import Optional, Tuple

MIN_CANDIDATE_AGE = 16
MAX_CANDIDATE_AGE = 100


def _age_from_dob(dob: date, today: Optional[date] = None) -> int:
    today = today or date.today()
    # Subtract a year when the birthday hasn't happened yet this year, otherwise
    # anyone born later in the calendar year reads as a year older than they are.
    had_birthday = (today.month, today.day) >= (dob.month, dob.day)
    return today.year - dob.year - (0 if had_birthday else 1)


def check_age_eligibility(
    dob: Optional[date], min_age: Optional[int], max_age: Optional[int]
) -> Tuple[bool, Optional[str]]:
    """
    Returns (eligible, reason_if_not). A job with no age criteria accepts everyone.
    A candidate with no date of birth on file is treated as ineligible for jobs that
    DO specify criteria — we can't verify them, and silently letting them through
    would make the criteria unenforceable.
    """
    if min_age is None and max_age is None:
        return True, None

    if dob is None:
        return False, "Add your date of birth to your profile to apply for this role."

    age = _age_from_dob(dob)
    if min_age is not None and age < min_age:
        return False, f"This role requires candidates to be at least {min_age} years old."
    if max_age is not None and age > max_age:
        return False, f"This role is limited to candidates up to {max_age} years old."
    return True, None


def describe_age_criteria(min_age: Optional[int], max_age: Optional[int]) -> Optional[str]:
    if min_age is not None and max_age is not None:
        return f"{min_age}-{max_age} yrs"
    if min_age is not None:
        return f"{min_age}+ yrs"
    if max_age is not None:
        return f"up to {max_age} yrs"
    return None
