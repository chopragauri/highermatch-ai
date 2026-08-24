from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator

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
    avatar_emoji: Optional[str] = None

    class Config:
        from_attributes = True


class AvatarUpdateRequest(BaseModel):
    avatar_emoji: str = Field(min_length=1, max_length=8)


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
    degree: str
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None


class CandidateProfileRequest(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    current_location: str
    preferred_location: Optional[str] = None
    headline: Optional[str] = None
    education: List[EducationEntry] = Field(min_length=1)
    self_reported_skills: List[str] = Field(default_factory=list)
    total_experience_yrs: Optional[float] = None


class CandidateProfileOut(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    current_location: Optional[str] = None
    preferred_location: Optional[str] = None
    headline: Optional[str] = None
    education: List[Dict[str, Any]] = Field(default_factory=list)
    self_reported_skills: List[str] = Field(default_factory=list)
    total_experience_yrs: Optional[float] = None
    profile_complete: bool

    class Config:
        from_attributes = True


class JobCreateRequest(BaseModel):
    title: str
    responsibilities: str
    required_skills: List[str]
    min_experience_yrs: float = 0
    max_experience_yrs: Optional[float] = None
    required_education: Optional[str] = None
    location: str
    job_type: str

    @field_validator("job_type")
    @classmethod
    def job_type_valid(cls, v: str) -> str:
        if v not in ("full-time", "part-time", "contract", "internship"):
            raise ValueError("invalid job_type")
        return v


class JobOut(BaseModel):
    id: UUIDStr
    title: str
    responsibilities: str
    required_skills: List[str]
    min_experience_yrs: float
    max_experience_yrs: Optional[float] = None
    required_education: Optional[str] = None
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
