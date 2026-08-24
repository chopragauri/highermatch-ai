from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_role
from ..parsing.pipeline import parse_resume

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB — plenty for a resume, keeps BYTEA rows small


@router.post("", response_model=schemas.ResumeParsedOut)
async def upload_resume(
    file: UploadFile = File(...),
    candidate: models.User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=422, detail="Only PDF or DOCX resumes are supported")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="Resume file is too large (max 5MB)")

    parsed = parse_resume(file_bytes, file.content_type)

    # Only one active resume per candidate — a re-upload supersedes the previous one.
    db.query(models.Resume).filter(
        models.Resume.candidate_user_id == candidate.id, models.Resume.is_active.is_(True)
    ).update({"is_active": False})

    resume = models.Resume(
        candidate_user_id=candidate.id,
        file_name=file.filename or "resume",
        file_bytes=file_bytes,
        file_mime=file.content_type,
        raw_text=parsed.raw_text,
        parsed_skills=parsed.skills,
        parsed_experience_yrs=parsed.experience_yrs,
        parsed_education=parsed.education,
        parsed_certifications=parsed.certifications,
        parsed_projects_keywords=parsed.project_keywords,
        resume_embedding=parsed.embedding.tolist(),
        is_active=True,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/me", response_model=schemas.ResumeParsedOut)
def my_resume(
    candidate: models.User = Depends(require_role("candidate")), db: Session = Depends(get_db)
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.candidate_user_id == candidate.id, models.Resume.is_active.is_(True))
        .order_by(models.Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    return resume
