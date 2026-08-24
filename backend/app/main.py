from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import analytics, applications, auth, candidates, jobs, matches, resumes

app = FastAPI(title="HR Job Portal with AI Resume Matching")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(applications.router)
app.include_router(matches.router)
app.include_router(analytics.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
