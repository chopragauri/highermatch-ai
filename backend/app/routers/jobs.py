from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_role
from ..matching.embeddings import embed_text
from ..matching.scoring import compute_match

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=schemas.JobOut)
def create_job(
    payload: schemas.JobCreateRequest,
    hr_user: models.User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    job = models.JobPosting(
        hr_user_id=hr_user.id,
        title=payload.title,
        responsibilities=payload.responsibilities,
        required_skills=[s.lower().strip() for s in payload.required_skills],
        min_experience_yrs=payload.min_experience_yrs,
        max_experience_yrs=payload.max_experience_yrs,
        required_education=payload.required_education,
        location=payload.location,
        job_type=payload.job_type,
        responsibilities_embedding=embed_text(payload.responsibilities).tolist(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=List[schemas.JobOut])
def list_own_jobs(
    hr_user: models.User = Depends(require_role("hr")), db: Session = Depends(get_db)
):
    return (
        db.query(models.JobPosting)
        .filter(models.JobPosting.hr_user_id == hr_user.id)
        .order_by(models.JobPosting.created_at.desc())
        .all()
    )


@router.get("/search", response_model=List[schemas.JobSearchResult])
def search_jobs(
    role: Optional[str] = None,
    skill: Optional[str] = None,
    location: Optional[str] = None,
    min_experience: Optional[float] = None,
    max_experience: Optional[float] = None,
    sort: str = Query("match_desc", pattern="^(match_desc|newest|experience_asc)$"),
    candidate: models.User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    query = db.query(models.JobPosting).filter(models.JobPosting.status == "open")
    if role:
        query = query.filter(models.JobPosting.title.ilike(f"%{role}%"))
    if skill:
        query = query.filter(models.JobPosting.required_skills.any(skill.lower().strip()))
    if location:
        query = query.filter(models.JobPosting.location.ilike(f"%{location}%"))
    if min_experience is not None:
        query = query.filter(models.JobPosting.min_experience_yrs >= min_experience)
    if max_experience is not None:
        query = query.filter(models.JobPosting.min_experience_yrs <= max_experience)

    jobs = query.all()

    resume = (
        db.query(models.Resume)
        .filter(models.Resume.candidate_user_id == candidate.id, models.Resume.is_active.is_(True))
        .order_by(models.Resume.created_at.desc())
        .first()
    )
    profile = (
        db.query(models.CandidateProfile)
        .filter(models.CandidateProfile.user_id == candidate.id)
        .first()
    )
    candidate_location = (
        (profile.preferred_location or profile.current_location) if profile else None
    )

    results = []
    for job in jobs:
        if resume:
            match = compute_match(resume, job, candidate_location)
        else:
            match = {
                "total": 0.0,
                "breakdown": {},
                "summary": "Upload a resume to see your match score for this job.",
            }
        results.append(
            schemas.JobSearchResult(job=schemas.JobOut.model_validate(job), match=schemas.MatchBreakdown(**match))
        )

    # Default sort is match_desc — this is the key candidate-facing requirement:
    # best-fit jobs surface first, before any filter is even touched.
    if sort == "match_desc":
        results.sort(key=lambda r: r.match.total, reverse=True)
    elif sort == "newest":
        results.sort(key=lambda r: r.job.created_at, reverse=True)
    elif sort == "experience_asc":
        results.sort(key=lambda r: r.job.min_experience_yrs)

    return results


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(
    job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}", response_model=schemas.JobOut)
def update_job(
    job_id: str,
    payload: schemas.JobCreateRequest,
    hr_user: models.User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    job = (
        db.query(models.JobPosting)
        .filter(models.JobPosting.id == job_id, models.JobPosting.hr_user_id == hr_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.title = payload.title
    job.responsibilities = payload.responsibilities
    job.required_skills = [s.lower().strip() for s in payload.required_skills]
    job.min_experience_yrs = payload.min_experience_yrs
    job.max_experience_yrs = payload.max_experience_yrs
    job.required_education = payload.required_education
    job.location = payload.location
    job.job_type = payload.job_type
    job.responsibilities_embedding = embed_text(payload.responsibilities).tolist()

    db.commit()
    db.refresh(job)
    return job


@router.patch("/{job_id}/status", response_model=schemas.JobOut)
def update_status(
    job_id: str,
    status: str,
    hr_user: models.User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    if status not in ("open", "closed"):
        raise HTTPException(status_code=422, detail="status must be 'open' or 'closed'")
    job = (
        db.query(models.JobPosting)
        .filter(models.JobPosting.id == job_id, models.JobPosting.hr_user_id == hr_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/applicants", response_model=List[schemas.ApplicantOut])
def list_applicants(
    job_id: str,
    hr_user: models.User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    job = (
        db.query(models.JobPosting)
        .filter(models.JobPosting.id == job_id, models.JobPosting.hr_user_id == hr_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    rows = (
        db.query(models.Application, models.User)
        .join(models.User, models.Application.candidate_user_id == models.User.id)
        .filter(models.Application.job_id == job_id)
        .order_by(models.Application.match_score_total.desc())
        .all()
    )
    return [
        schemas.ApplicantOut(
            id=str(app.id),
            job_id=str(app.job_id),
            candidate_id=str(user.id),
            candidate_name=user.full_name,
            candidate_email=user.email,
            candidate_phone=user.phone,
            match_score_total=float(app.match_score_total),
            match_score_breakdown=app.match_score_breakdown,
            match_summary_text=app.match_summary_text,
            status=app.status,
            applied_at=app.applied_at,
        )
        for app, user in rows
    ]
