from fastapi import FastAPI

from .agent import JobCompatibilityAgent
from .schemas import (
    CandidateProfile,
    JobCompatibilityRequest,
    JobCompatibilityResponse,
)


app = FastAPI(
    title="Job Compatibility Agent",
    description="Member C - capability-based job compatibility service",
    version="1.0.0",
)

agent = JobCompatibilityAgent()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "job_compatibility_agent",
        "version": "1.0.0",
    }


@app.post(
    "/match-jobs",
    response_model=JobCompatibilityResponse,
)
def match_jobs(request: JobCompatibilityRequest):

    candidate = CandidateProfile(
        candidate_id=request.candidate_id,
        verified_skills=request.verified_skills,
        experience_years=request.experience_years,
    )

    return agent.match_jobs(candidate)