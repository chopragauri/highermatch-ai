from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator, model_validator

from .ages import MAX_CANDIDATE_AGE, MIN_CANDIDATE_AGE, _age_from_dob

# SQLAlchemy returns UUID objects for UUID-typed columns; Pydantic v2's `str` field
# does not auto-coerce those, so every id field uses this alias to stringify first.
UUIDStr = Annotated[str, BeforeValidator(str)]


class UserOut(BaseModel):
    id: UUIDStr
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    profile_complete: Optional[bool] = None

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str  # 'hr' | 'candidate'
    phone: Optional[str] = None

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in ("hr", "candidate"):
            raise ValueError("role must be 'hr' or 'candidate'")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class EducationEntry(BaseModel):
    degree: str = Field(min_length=1)
    field_of_study: Optional[str] = None
    institution: str = Field(min_length=1)
    start_year: int = Field(ge=1950, le=2100)
    end_year: int = Field(ge=1950, le=2100)
    grade: Optional[str] = None

    @model_validator(mode="after")
    def years_ordered(self):
        if self.end_year < self.start_year:
            raise ValueError("end_year cannot be before start_year")
        return self


class CandidateProfileRequest(BaseModel):
    """Server-side validation mirrors the client form exactly — the browser checks are
    a convenience, this is the actual gate. Only gender and headline are optional."""

    date_of_birth: date
    gender: Optional[str] = None
    current_location: str = Field(min_length=1, max_length=120)
    preferred_location: str = Field(min_length=1, max_length=120)
    headline: Optional[str] = Field(default=None, max_length=200)
    tenth_percentage: float = Field(ge=0, le=100)
    twelfth_percentage: float = Field(ge=0, le=100)
    education: List[EducationEntry] = Field(min_length=1)
    self_reported_skills: List[str] = Field(min_length=1)
    total_experience_yrs: float = Field(ge=0, le=60)

    @field_validator("date_of_birth")
    @classmethod
    def dob_realistic(cls, v: date) -> date:
        age = _age_from_dob(v)
        if age < MIN_CANDIDATE_AGE:
            raise ValueError(f"Candidates must be at least {MIN_CANDIDATE_AGE} years old")
        if age > MAX_CANDIDATE_AGE:
            raise ValueError("Date of birth is not valid")
        return v

    @field_validator("self_reported_skills")
    @classmethod
    def skills_non_empty(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("At least one skill is required")
        return cleaned


class CandidateProfileOut(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    current_location: Optional[str] = None
    preferred_location: Optional[str] = None
    headline: Optional[str] = None
    tenth_percentage: Optional[float] = None
    twelfth_percentage: Optional[float] = None
    education: List[Dict[str, Any]] = Field(default_factory=list)
    self_reported_skills: List[str] = Field(default_factory=list)
    total_experience_yrs: Optional[float] = None
    profile_complete: bool

    class Config:
        from_attributes = True


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    responsibilities: str = Field(min_length=20)
    required_skills: List[str] = Field(min_length=1)
    min_experience_yrs: float = Field(default=0, ge=0, le=60)
    max_experience_yrs: Optional[float] = Field(default=None, ge=0, le=60)
    required_education: Optional[str] = None
    min_age: Optional[int] = Field(default=None, ge=MIN_CANDIDATE_AGE, le=MAX_CANDIDATE_AGE)
    max_age: Optional[int] = Field(default=None, ge=MIN_CANDIDATE_AGE, le=MAX_CANDIDATE_AGE)
    location: str = Field(min_length=1, max_length=120)
    job_type: str

    @field_validator("job_type")
    @classmethod
    def job_type_valid(cls, v: str) -> str:
        if v not in ("full-time", "part-time", "contract", "internship"):
            raise ValueError("invalid job_type")
        return v

    @field_validator("required_skills")
    @classmethod
    def skills_non_empty(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("At least one required skill is needed")
        return cleaned

    @model_validator(mode="after")
    def ranges_ordered(self):
        if self.max_experience_yrs is not None and self.max_experience_yrs < self.min_experience_yrs:
            raise ValueError("max_experience_yrs cannot be less than min_experience_yrs")
        if self.min_age is not None and self.max_age is not None and self.max_age < self.min_age:
            raise ValueError("max_age cannot be less than min_age")
        return self


class JobOut(BaseModel):
    id: UUIDStr
    title: str
    responsibilities: str
    required_skills: List[str]
    min_experience_yrs: float
    max_experience_yrs: Optional[float] = None
    required_education: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    location: str
    job_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MatchBreakdown(BaseModel):
    total: float
    breakdown: Dict[str, Any]
    summary: str
    ai_generated: bool = False
    age_eligible: bool = True
    age_ineligible_reason: Optional[str] = None


class JobSearchResult(BaseModel):
    job: JobOut
    match: MatchBreakdown


class ResumeParsedOut(BaseModel):
    id: UUIDStr
    file_name: str
    parsed_skills: List[str]
    parsed_experience_yrs: Optional[float] = None
    parsed_education: List[Dict[str, Any]]
    parsed_certifications: List[str]

    class Config:
        from_attributes = True


class ApplicationOut(BaseModel):
    id: UUIDStr
    job_id: UUIDStr
    match_score_total: float
    match_summary_text: str
    ai_generated: bool = False
    status: str
    applied_at: datetime

    class Config:
        from_attributes = True


class ApplicantOut(BaseModel):
    """Applicant list row for the HR view — includes who applied, not just a score."""

    id: UUIDStr
    job_id: UUIDStr
    candidate_id: UUIDStr
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    match_score_total: float
    match_score_breakdown: Dict[str, Any]
    match_summary_text: str
    ai_generated: bool = False
    status: str
    applied_at: datetime


class MyApplicationOut(BaseModel):
    """The candidate's own applications list — includes job title/location/status so
    the dashboard doesn't need a second round-trip per row to show anything useful."""

    id: UUIDStr
    job_id: UUIDStr
    job_title: str
    job_location: str
    job_status: str
    match_score_total: float
    match_summary_text: str
    ai_generated: bool = False
    status: str
    applied_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("applied", "viewed", "shortlisted", "rejected"):
            raise ValueError("invalid status")
        return v


class JobApplicantCount(BaseModel):
    job_id: UUIDStr
    job_title: str
    applicant_count: int
    average_match_score: float


class SkillGapEntry(BaseModel):
    skill: str
    missing_count: int


class HrAnalyticsOut(BaseModel):
    total_jobs: int
    open_jobs: int
    closed_jobs: int
    total_applicants: int
    average_match_score: float
    status_breakdown: Dict[str, int]
    applicants_per_job: List[JobApplicantCount]
    top_missing_skills: List[SkillGapEntry]
