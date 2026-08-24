from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_role
from ..matching.scoring import compute_match

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("/{job_id}", response_model=schemas.MatchBreakdown)
def get_match(
    job_id: str,
    candidate: models.User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = (
        db.query(models.Resume)
        .filter(models.Resume.candidate_user_id == candidate.id, models.Resume.is_active.is_(True))
        .order_by(models.Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=422, detail="Upload a resume first")

    profile = (
        db.query(models.CandidateProfile)
        .filter(models.CandidateProfile.user_id == candidate.id)
        .first()
    )
    candidate_location = (
        (profile.preferred_location or profile.current_location) if profile else None
    )

    # use_llm=True here is safe — this endpoint is called for one job at a time
    # (the job detail page), never for a whole search results list.
    match = compute_match(resume, job, candidate_location, use_llm=True)
    return schemas.MatchBreakdown(**match)
