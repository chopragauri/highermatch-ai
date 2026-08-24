from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_role
from ..matching.scoring import compute_match

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplyRequest(BaseModel):
    job_id: str


@router.post("", response_model=schemas.ApplicationOut)
def apply(
    payload: ApplyRequest,
    candidate: models.User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    job = (
        db.query(models.JobPosting)
        .filter(models.JobPosting.id == payload.job_id, models.JobPosting.status == "open")
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or closed")

    resume = (
        db.query(models.Resume)
        .filter(models.Resume.candidate_user_id == candidate.id, models.Resume.is_active.is_(True))
        .order_by(models.Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=422, detail="Upload a resume before applying")

    existing = (
        db.query(models.Application)
        .filter(
            models.Application.job_id == job.id,
            models.Application.candidate_user_id == candidate.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this job")

    profile = (
        db.query(models.CandidateProfile)
        .filter(models.CandidateProfile.user_id == candidate.id)
        .first()
    )
    candidate_location = (
        (profile.preferred_location or profile.current_location) if profile else None
    )

    match = compute_match(resume, job, candidate_location)

    application = models.Application(
        job_id=job.id,
        candidate_user_id=candidate.id,
        resume_id=resume.id,
        match_score_total=match["total"],
        match_score_breakdown=match["breakdown"],
        match_summary_text=match["summary"],
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/me", response_model=List[schemas.MyApplicationOut])
def my_applications(
    candidate: models.User = Depends(require_role("candidate")), db: Session = Depends(get_db)
):
    rows = (
        db.query(models.Application, models.JobPosting)
        .join(models.JobPosting, models.Application.job_id == models.JobPosting.id)
        .filter(models.Application.candidate_user_id == candidate.id)
        .order_by(models.Application.applied_at.desc())
        .all()
    )
    return [
        schemas.MyApplicationOut(
            id=str(app.id),
            job_id=str(app.job_id),
            job_title=job.title,
            job_location=job.location,
            job_status=job.status,
            match_score_total=float(app.match_score_total),
            match_summary_text=app.match_summary_text,
            status=app.status,
            applied_at=app.applied_at,
        )
        for app, job in rows
    ]


@router.patch("/{application_id}/status", response_model=schemas.ApplicationOut)
def update_application_status(
    application_id: str,
    payload: schemas.ApplicationStatusUpdate,
    hr_user: models.User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    application = (
        db.query(models.Application)
        .join(models.JobPosting, models.Application.job_id == models.JobPosting.id)
        .filter(
            models.Application.id == application_id,
            models.JobPosting.hr_user_id == hr_user.id,
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application.status = payload.status
    db.commit()
    db.refresh(application)
    return application
