from collections import Counter
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_role

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/hr", response_model=schemas.HrAnalyticsOut)
def hr_analytics(
    hr_user: models.User = Depends(require_role("hr")), db: Session = Depends(get_db)
):
    jobs = db.query(models.JobPosting).filter(models.JobPosting.hr_user_id == hr_user.id).all()
    job_ids = [j.id for j in jobs]

    applications: List[models.Application] = (
        db.query(models.Application).filter(models.Application.job_id.in_(job_ids)).all()
        if job_ids
        else []
    )

    open_jobs = sum(1 for j in jobs if j.status == "open")
    total_applicants = len(applications)
    average_match_score = (
        round(sum(float(a.match_score_total) for a in applications) / total_applicants, 1)
        if total_applicants
        else 0.0
    )

    status_breakdown = {"applied": 0, "viewed": 0, "shortlisted": 0, "rejected": 0}
    for a in applications:
        status_breakdown[a.status] = status_breakdown.get(a.status, 0) + 1

    # Per-job applicant count + average score, sorted busiest-first — the ranking
    # itself is a useful signal for HR (which postings are actually getting traction).
    apps_by_job: dict = {}
    for a in applications:
        apps_by_job.setdefault(a.job_id, []).append(a)

    applicants_per_job = []
    for job in jobs:
        job_apps = apps_by_job.get(job.id, [])
        if not job_apps:
            continue
        applicants_per_job.append(
            schemas.JobApplicantCount(
                job_id=str(job.id),
                job_title=job.title,
                applicant_count=len(job_apps),
                average_match_score=round(
                    sum(float(a.match_score_total) for a in job_apps) / len(job_apps), 1
                ),
            )
        )
    applicants_per_job.sort(key=lambda r: r.applicant_count, reverse=True)

    # Skill-gap analysis: which required skills do applicants most commonly lack,
    # aggregated across every application's stored match breakdown.
    missing_skill_counter: Counter = Counter()
    for a in applications:
        missing = (a.match_score_breakdown or {}).get("skills", {}).get("missing", [])
        missing_skill_counter.update(missing)
    top_missing_skills = [
        schemas.SkillGapEntry(skill=skill, missing_count=count)
        for skill, count in missing_skill_counter.most_common(10)
    ]

    return schemas.HrAnalyticsOut(
        total_jobs=len(jobs),
        open_jobs=open_jobs,
        closed_jobs=len(jobs) - open_jobs,
        total_applicants=total_applicants,
        average_match_score=average_match_score,
        status_breakdown=status_breakdown,
        applicants_per_job=applicants_per_job,
        top_missing_skills=top_missing_skills,
    )
