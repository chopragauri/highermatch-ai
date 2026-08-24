from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_role

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.put("/me/profile", response_model=schemas.CandidateProfileOut)
def update_profile(
    payload: schemas.CandidateProfileRequest,
    user: models.User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(models.CandidateProfile)
        .filter(models.CandidateProfile.user_id == user.id)
        .first()
    )
    if not profile:
        profile = models.CandidateProfile(user_id=user.id)
        db.add(profile)

    profile.date_of_birth = payload.date_of_birth
    profile.gender = payload.gender
    profile.current_location = payload.current_location
    profile.preferred_location = payload.preferred_location
    profile.headline = payload.headline
    profile.tenth_percentage = payload.tenth_percentage
    profile.twelfth_percentage = payload.twelfth_percentage
    profile.education = [e.model_dump(mode="json") for e in payload.education]
    profile.self_reported_skills = [s.lower().strip() for s in payload.self_reported_skills]
    profile.total_experience_yrs = payload.total_experience_yrs
    profile.profile_complete = True

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/profile", response_model=schemas.CandidateProfileOut)
def get_profile(
    user: models.User = Depends(require_role("candidate")), db: Session = Depends(get_db)
):
    profile = (
        db.query(models.CandidateProfile)
        .filter(models.CandidateProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
