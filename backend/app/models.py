import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'hr' | 'candidate'
    full_name = Column(String, nullable=False)
    org_domain = Column(String, nullable=True)  # set for HR users, derived from email
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("role in ('hr','candidate')", name="ck_users_role"),)

    candidate_profile = relationship(
        "CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    job_postings = relationship(
        "JobPosting", back_populates="hr_user", cascade="all, delete-orphan"
    )
    applications = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    current_location = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    tenth_percentage = Column(Numeric(5, 2), nullable=True)
    twelfth_percentage = Column(Numeric(5, 2), nullable=True)
    # [{degree, field_of_study, institution, start_year, end_year, grade}]
    education = Column(JSONB, nullable=False, default=list)
    self_reported_skills = Column(ARRAY(String), nullable=False, default=list)
    total_experience_yrs = Column(Numeric(4, 1), nullable=True)
    profile_complete = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="candidate_profile")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hr_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    responsibilities = Column(Text, nullable=False)
    required_skills = Column(ARRAY(String), nullable=False, default=list)
    min_experience_yrs = Column(Numeric(4, 1), nullable=False, default=0)
    max_experience_yrs = Column(Numeric(4, 1), nullable=True)
    required_education = Column(String, nullable=True)
    # Age eligibility criteria — enforced as a hard block on apply, not just scored.
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    location = Column(String, nullable=False)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    # Stored as a plain float array (not pgvector) so matching works on any Postgres
    # instance with zero extension setup — cosine similarity is computed in Python.
    responsibilities_embedding = Column(ARRAY(Numeric), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "job_type in ('full-time','part-time','contract','internship')", name="ck_jobs_type"
        ),
        CheckConstraint("status in ('open','closed')", name="ck_jobs_status"),
    )

    hr_user = relationship("User", back_populates="job_postings")
    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_bytes = Column(LargeBinary, nullable=False)
    file_mime = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_skills = Column(ARRAY(String), nullable=False, default=list)
    parsed_experience_yrs = Column(Numeric(4, 1), nullable=True)
    parsed_education = Column(JSONB, nullable=False, default=list)
    parsed_certifications = Column(ARRAY(String), nullable=False, default=list)
    parsed_projects_keywords = Column(ARRAY(String), nullable=False, default=list)
    resume_embedding = Column(ARRAY(Numeric), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("User", back_populates="resumes")


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    candidate_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    match_score_total = Column(Numeric(5, 2), nullable=False)
    match_score_breakdown = Column(JSONB, nullable=False)
    match_summary_text = Column(Text, nullable=False)
    ai_generated = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="applied")
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_user_id", name="uq_application_job_candidate"),
        CheckConstraint(
            "status in ('applied','viewed','shortlisted','rejected')", name="ck_app_status"
        ),
    )

    job = relationship("JobPosting", back_populates="applications")
    candidate = relationship("User", back_populates="applications")
    resume = relationship("Resume")
