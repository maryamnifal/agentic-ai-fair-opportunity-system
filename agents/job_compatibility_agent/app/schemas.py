from typing import List, Optional

from pydantic import BaseModel, Field


class VerifiedSkill(BaseModel):
    """
    Skill information produced by Member B's Skill Verification Agent.
    """

    skill: str
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""


class CandidateProfile(BaseModel):
    """
    Candidate capability information consumed by Member C.

    Member C uses verified skills from Member B.
    Raw portfolio text is not required here.
    """

    candidate_id: str
    verified_skills: List[VerifiedSkill]
    experience_years: float = Field(default=0.0, ge=0.0)


class Job(BaseModel):
    """
    Job-side data used by the Job Compatibility Agent.
    """

    job_id: str
    title: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str] = Field(default_factory=list)
    skill_categories: List[str] = Field(default_factory=list)
    minimum_experience_years: float = Field(default=0.0, ge=0.0)


class MatchedJob(BaseModel):
    """
    Explainable compatibility result for one job.
    """

    job_id: str
    title: str

    compatibility_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    structured_score: float = Field(ge=0.0, le=1.0)

    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

    explanation: str


class JobCompatibilityRequest(BaseModel):
    """
    Request accepted by Member C's API.
    """

    candidate_id: str
    verified_skills: List[VerifiedSkill]
    experience_years: float = Field(default=0.0, ge=0.0)


class JobCompatibilityResponse(BaseModel):
    """
    Final response returned by Member C.
    """

    candidate_id: str
    matched_jobs: List[MatchedJob]