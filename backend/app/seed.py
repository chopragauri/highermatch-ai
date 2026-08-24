"""
Synthetic sample data for local dev and the hackathon demo.

Creates 1 HR account, 10 varied job postings, and 6 candidates with realistic
(but fully synthetic) resume text spanning strong-fit, weak-fit, overqualified,
and career-mismatch profiles — so the match-score sorting is visibly meaningful
in the demo rather than everyone landing near 50%.

Run: python -m app.seed
"""
import random
from datetime import date

from . import models, security
from .database import Base, SessionLocal, engine
from .matching.embeddings import embed_text
from .parsing.extractors import (
    extract_certifications,
    extract_education,
    extract_experience_years,
    extract_project_keywords,
    extract_skills,
)

random.seed(42)

# Jobs without explicit min_age/max_age accept all ages.
DEFAULT_AGE_CRITERIA = {"min_age": None, "max_age": None}

JOBS = [
    dict(
        title="Backend Engineer",
        responsibilities=(
            "Design and build scalable REST APIs, own service reliability, write clean "
            "Python and FastAPI code, collaborate with frontend and data teams, "
            "participate in code review and on-call rotation."
        ),
        required_skills=["python", "fastapi", "postgresql", "docker", "rest api"],
        min_experience_yrs=3, max_experience_yrs=6,
        required_education="Bachelor's", location="Bengaluru", job_type="full-time",
    ),
    dict(
        title="Frontend Engineer",
        responsibilities=(
            "Build responsive web interfaces with React and Next.js, work closely with "
            "designers, optimize performance, write unit and integration tests."
        ),
        required_skills=["react", "next.js", "typescript", "css", "html"],
        min_experience_yrs=2, max_experience_yrs=5,
        required_education="Bachelor's", location="Remote", job_type="full-time",
    ),
    dict(
        title="Data Scientist",
        responsibilities=(
            "Analyze large datasets, build machine learning models, communicate insights "
            "to stakeholders, own the full ML lifecycle from data exploration to deployment."
        ),
        required_skills=["python", "machine learning", "pandas", "sql", "scikit-learn"],
        min_experience_yrs=2, max_experience_yrs=6,
        required_education="Master's", location="Hyderabad", job_type="full-time",
    ),
    dict(
        title="DevOps Engineer",
        responsibilities=(
            "Manage CI/CD pipelines, own cloud infrastructure on AWS, implement monitoring "
            "and alerting, automate deployments with Terraform and Kubernetes."
        ),
        required_skills=["aws", "kubernetes", "terraform", "docker", "ci/cd"],
        min_experience_yrs=3, max_experience_yrs=8,
        required_education="Bachelor's", location="Pune", job_type="full-time",
    ),
    dict(
        title="Product Manager",
        responsibilities=(
            "Own product roadmap, gather requirements from stakeholders, write PRDs, "
            "coordinate with engineering and design to ship features on schedule."
        ),
        required_skills=["product management", "agile", "roadmapping", "stakeholder management"],
        min_experience_yrs=4, max_experience_yrs=10,
        required_education="MBA", location="Bengaluru", job_type="full-time",
    ),
    dict(
        title="QA Engineer",
        responsibilities=(
            "Write and maintain automated test suites, perform manual and regression "
            "testing, collaborate with developers to reproduce and triage bugs."
        ),
        required_skills=["selenium", "python", "test automation", "manual testing"],
        min_experience_yrs=1, max_experience_yrs=4,
        required_education="Bachelor's", location="Gurgaon", job_type="full-time",
    ),
    dict(
        title="Machine Learning Engineer",
        responsibilities=(
            "Productionize ML models, build training and inference pipelines, optimize "
            "model serving latency, work with data scientists to deploy new models."
        ),
        required_skills=["python", "pytorch", "machine learning", "docker", "mlops"],
        min_experience_yrs=3, max_experience_yrs=7,
        required_education="Master's", location="Remote", job_type="full-time",
    ),
    dict(
        title="Full Stack Developer Intern",
        responsibilities=(
            "Assist in building features across the stack using React and Node.js, "
            "write tests, fix bugs, and learn from senior engineers in a fast-paced startup."
        ),
        required_skills=["javascript", "react", "node.js", "git"],
        min_experience_yrs=0, max_experience_yrs=1,
        required_education="Bachelor's", location="Bengaluru", job_type="internship",
        min_age=18, max_age=25,
    ),
    dict(
        title="UI/UX Designer",
        responsibilities=(
            "Design intuitive user flows and interfaces, run user research, build "
            "prototypes in Figma, collaborate closely with product and engineering."
        ),
        required_skills=["figma", "ui design", "ux research", "prototyping"],
        min_experience_yrs=2, max_experience_yrs=6,
        required_education="Bachelor's", location="Remote", job_type="full-time",
    ),
    dict(
        title="Cloud Solutions Architect",
        responsibilities=(
            "Design cloud-native architecture on Azure, lead migration projects, define "
            "best practices for security and scalability, mentor engineering teams."
        ),
        required_skills=["azure", "cloud architecture", "kubernetes", "security"],
        min_experience_yrs=6, max_experience_yrs=12,
        required_education="Bachelor's", location="Hyderabad", job_type="full-time",
        min_age=28,
    ),
]

CANDIDATES = [
    dict(
        email="priya.sharma@example.com", phone="+91-9876500001", full_name="Priya Sharma",
        date_of_birth=date(1998, 3, 14), tenth_percentage=88.0, twelfth_percentage=91.0,
        current_location="Bengaluru", preferred_location="Bengaluru",
        headline="Backend engineer specializing in Python microservices",
        education=[{"degree": "B.Tech", "field_of_study": "Computer Science",
                     "institution": "NIT Trichy", "start_year": 2016, "end_year": 2020,
                     "grade": "8.7 CGPA"}],
        self_reported_skills=["python", "fastapi", "postgresql", "docker", "rest api", "aws"],
        total_experience_yrs=4,
        resume_text=(
            "Priya Sharma - Backend Engineer\n"
            "4 years of experience building scalable backend systems.\n"
            "Skills: Python, FastAPI, PostgreSQL, Docker, REST API, AWS, Redis\n"
            "Education: B.Tech in Computer Science, NIT Trichy, 2016-2020\n"
            "Work Experience: Backend Engineer at TechCorp, 2020-2024. "
            "Designed and built REST APIs serving 2M requests/day, owned service "
            "reliability, migrated legacy services to FastAPI, mentored junior engineers.\n"
            "Certifications: AWS Certified Solutions Architect\n"
            "Projects: Built a real-time notification service using FastAPI and Redis pub/sub."
        ),
    ),
    dict(
        email="arjun.mehta@example.com", phone="+91-9876500002", full_name="Arjun Mehta",
        date_of_birth=date(1996, 7, 2), tenth_percentage=92.5, twelfth_percentage=94.0,
        current_location="Hyderabad", preferred_location="Hyderabad",
        headline="Data scientist with a focus on NLP and predictive modeling",
        education=[{"degree": "M.Tech", "field_of_study": "Data Science",
                     "institution": "IIIT Hyderabad", "start_year": 2018, "end_year": 2020,
                     "grade": "9.1 CGPA"}],
        self_reported_skills=["python", "machine learning", "pandas", "sql", "scikit-learn", "nlp"],
        total_experience_yrs=3,
        resume_text=(
            "Arjun Mehta - Data Scientist\n"
            "3 years experience in machine learning and data analysis.\n"
            "Skills: Python, Machine Learning, Pandas, SQL, Scikit-learn, NLP, TensorFlow\n"
            "Education: M.Tech in Data Science, IIIT Hyderabad, 2018-2020\n"
            "Work Experience: Data Scientist at Analytics Co, 2021-2024. "
            "Built predictive churn models, analyzed large datasets with Pandas and SQL, "
            "presented insights to stakeholders, deployed models to production.\n"
            "Certifications: Google Cloud Certified Professional Data Engineer\n"
            "Projects: Built an NLP-based sentiment analysis pipeline for customer reviews."
        ),
    ),
    dict(
        email="sneha.iyer@example.com", phone="+91-9876500003", full_name="Sneha Iyer",
        date_of_birth=date(1999, 11, 23), tenth_percentage=85.0, twelfth_percentage=87.5,
        current_location="Remote", preferred_location="Remote",
        headline="Frontend developer passionate about React and design systems",
        education=[{"degree": "B.E.", "field_of_study": "Information Technology",
                     "institution": "VJTI Mumbai", "start_year": 2017, "end_year": 2021,
                     "grade": "8.3 CGPA"}],
        self_reported_skills=["react", "next.js", "typescript", "css", "html", "javascript"],
        total_experience_yrs=2.5,
        resume_text=(
            "Sneha Iyer - Frontend Developer\n"
            "2.5 years of experience building web interfaces.\n"
            "Skills: React, Next.js, TypeScript, CSS, HTML, JavaScript, Tailwind\n"
            "Education: B.E. in Information Technology, VJTI Mumbai, 2017-2021\n"
            "Work Experience: Frontend Developer at WebWorks, 2022-2024. "
            "Built responsive interfaces with React and Next.js, optimized performance, "
            "collaborated with designers, wrote unit tests with Jest.\n"
            "Projects: Built a design system component library used across 5 products."
        ),
    ),
    dict(
        email="rahul.verma@example.com", phone="+91-9876500004", full_name="Rahul Verma",
        date_of_birth=date(2002, 5, 9), tenth_percentage=78.0, twelfth_percentage=81.0,
        current_location="Pune", preferred_location="Pune",
        headline="Recent graduate exploring software engineering roles",
        education=[{"degree": "B.Tech", "field_of_study": "Computer Science",
                     "institution": "COEP Pune", "start_year": 2020, "end_year": 2024,
                     "grade": "7.5 CGPA"}],
        self_reported_skills=["javascript", "react", "node.js", "git"],
        total_experience_yrs=0.5,
        resume_text=(
            "Rahul Verma - Software Engineer (Fresher)\n"
            "0.5 years experience, recent Computer Science graduate.\n"
            "Skills: JavaScript, React, Node.js, Git, HTML, CSS\n"
            "Education: B.Tech in Computer Science, COEP Pune, 2020-2024\n"
            "Work Experience: Full Stack Intern at StartupXYZ, 2024. Built features "
            "across the stack using React and Node.js, fixed bugs, wrote tests.\n"
            "Projects: Built a personal portfolio site and a to-do app with React."
        ),
    ),
    dict(
        email="ananya.gupta@example.com", phone="+91-9876500005", full_name="Ananya Gupta",
        date_of_birth=date(1989, 1, 30), tenth_percentage=90.0, twelfth_percentage=89.0,
        current_location="Bengaluru", preferred_location="Bengaluru",
        headline="Senior product manager with a decade of experience in B2B SaaS",
        education=[{"degree": "MBA", "field_of_study": "Marketing",
                     "institution": "IIM Bangalore", "start_year": 2011, "end_year": 2013,
                     "grade": "3.7 GPA"}],
        self_reported_skills=["product management", "agile", "roadmapping", "stakeholder management"],
        total_experience_yrs=11,
        resume_text=(
            "Ananya Gupta - Senior Product Manager\n"
            "11 years experience leading B2B SaaS products.\n"
            "Skills: Product Management, Agile, Roadmapping, Stakeholder Management, Scrum\n"
            "Education: MBA in Marketing, IIM Bangalore, 2011-2013\n"
            "Work Experience: Senior Product Manager at SaaSCo, 2013-2024. Owned "
            "product roadmap for a $50M ARR product line, wrote PRDs, coordinated with "
            "engineering and design across 3 continents.\n"
            "Certifications: Certified Scrum Master\n"
            "Projects: Led the launch of a new analytics module adopted by 200+ customers."
        ),
    ),
    dict(
        email="vikram.rao@example.com", phone="+91-9876500006", full_name="Vikram Rao",
        date_of_birth=date(1997, 9, 17), tenth_percentage=72.0, twelfth_percentage=75.0,
        current_location="Chennai", preferred_location="Bengaluru",
        headline="Marketing specialist exploring a pivot into tech-adjacent roles",
        education=[{"degree": "Bachelor's", "field_of_study": "Business Administration",
                     "institution": "Anna University", "start_year": 2015, "end_year": 2019,
                     "grade": "7.0 CGPA"}],
        self_reported_skills=["digital marketing", "seo", "content strategy", "excel"],
        total_experience_yrs=5,
        resume_text=(
            "Vikram Rao - Marketing Specialist\n"
            "5 years experience in digital marketing.\n"
            "Skills: Digital Marketing, SEO, Content Strategy, Excel, Google Analytics\n"
            "Education: Bachelor's in Business Administration, Anna University, 2015-2019\n"
            "Work Experience: Marketing Specialist at BrandCo, 2019-2024. Managed SEO "
            "campaigns, wrote content strategy, ran Google Ads campaigns.\n"
            "Projects: Increased organic traffic by 40% through SEO optimization."
        ),
    ),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("Database already has data — skipping seed. Wipe the DB first to reseed.")
            return

        hr_user = models.User(
            email="hr@yahoo.com",
            phone="+91-9876543210",
            password_hash=security.hash_password("HrPass123!"),
            role="hr",
            full_name="Meera Nair",
            org_domain="yahoo.com",
        )
        db.add(hr_user)
        db.flush()

        for job_data in JOBS:
            embedding = embed_text(job_data["responsibilities"]).tolist()
            db.add(models.JobPosting(hr_user_id=hr_user.id, responsibilities_embedding=embedding, **job_data))

        for c in CANDIDATES:
            user = models.User(
                email=c["email"], phone=c["phone"],
                password_hash=security.hash_password("Candidate123!"),
                role="candidate", full_name=c["full_name"],
            )
            db.add(user)
            db.flush()

            db.add(models.CandidateProfile(
                user_id=user.id,
                date_of_birth=c["date_of_birth"],
                tenth_percentage=c["tenth_percentage"],
                twelfth_percentage=c["twelfth_percentage"],
                current_location=c["current_location"],
                preferred_location=c["preferred_location"],
                headline=c["headline"],
                education=c["education"],
                self_reported_skills=c["self_reported_skills"],
                total_experience_yrs=c["total_experience_yrs"],
                profile_complete=True,
            ))

            raw_text = c["resume_text"]
            db.add(models.Resume(
                candidate_user_id=user.id,
                file_name=f"{c['full_name'].replace(' ', '_')}_resume.txt",
                file_bytes=raw_text.encode("utf-8"),
                file_mime="text/plain",
                raw_text=raw_text,
                parsed_skills=extract_skills(raw_text),
                parsed_experience_yrs=extract_experience_years(raw_text),
                parsed_education=extract_education(raw_text),
                parsed_certifications=extract_certifications(raw_text),
                parsed_projects_keywords=extract_project_keywords(raw_text),
                resume_embedding=embed_text(raw_text).tolist(),
                is_active=True,
            ))

        db.commit()
        print(f"Seeded {len(JOBS)} jobs, {len(CANDIDATES)} candidates, and 1 HR user.")
        print("HR login:        hr@yahoo.com / HrPass123!")
        print("Candidate login: priya.sharma@example.com / Candidate123! (strong fit for Backend Engineer)")
        print("Candidate login: vikram.rao@example.com / Candidate123! (weak fit for all tech roles)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
