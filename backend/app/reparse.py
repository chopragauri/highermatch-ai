"""
Re-runs the parsing pipeline against every resume's stored file_bytes and updates
the parsed_* columns in place. Use this after a parsing-logic change (skills
taxonomy, experience regex, certification list, etc.) so already-uploaded resumes
pick up the fix without anyone needing to re-upload.

Run: python -m app.reparse
"""
from .database import SessionLocal
from . import models
from .parsing.pipeline import parse_resume


def run():
    db = SessionLocal()
    try:
        resumes = db.query(models.Resume).all()
        for resume in resumes:
            parsed = parse_resume(resume.file_bytes, resume.file_mime)
            resume.raw_text = parsed.raw_text
            resume.parsed_skills = parsed.skills
            resume.parsed_experience_yrs = parsed.experience_yrs
            resume.parsed_education = parsed.education
            resume.parsed_certifications = parsed.certifications
            resume.parsed_projects_keywords = parsed.project_keywords
            resume.resume_embedding = parsed.embedding.tolist()
            print(f"Re-parsed {resume.file_name}: {parsed.experience_yrs} yrs, "
                  f"{len(parsed.skills)} skills, certs={parsed.certifications}")
        db.commit()
        print(f"Done — re-parsed {len(resumes)} resume(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
