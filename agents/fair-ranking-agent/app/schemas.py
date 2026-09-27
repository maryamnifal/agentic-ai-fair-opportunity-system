"""
Pydantic schemas for Member D's Fair Ranking Agent.

VerifiedSkill and MatchedJob are kept field-compatible with Member B's
(agents/skill_verification_agent) and Member C's (agents/job_compatibility_agent)
schemas respectively, so their real JSON output can be passed straight into
this service without any conversion.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---- Passed through from Member B ----
class VerifiedSkill(BaseModel):
    skill: str
    status: str  # supported | weakly_supported | unsupported | contradicted
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""


# ---- Passed through from Member C ----
class MatchedJob(BaseModel):
    job_id: str
    title: str
    compatibility_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    structured_score: float = Field(ge=0.0, le=1.0)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    explanation: str = ""


# ---- Member D's own output: a re-ranked job with fairness reasoning ----
class FairMatchedJob(BaseModel):
    job_id: str
    title: str

    compatibility_score: float = Field(
        ge=0.0, le=1.0, description="Member C's original score, unchanged, for transparency"
    )
    fair_score: float = Field(
        ge=0.0, le=1.0, description="compatibility_score adjusted by the fairness multiplier"
    )
    original_rank: int
    fair_rank: int

    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    explanation: str = ""
    fairness_note: str = ""


class FairnessBreakdown(BaseModel):
    """Transparency block: exactly how the fairness multiplier was derived."""

    claimed_skill_count: int
    supported_count: int
    weakly_supported_count: int
    unsupported_count: int
    contradicted_count: int
    evidence_quality: float = Field(ge=0.0, le=1.0)
    overclaim_ratio: float = Field(ge=0.0, le=1.0)
    fairness_multiplier: float
    summary: str


class FairRankingRequest(BaseModel):
    """
    Request body for POST /api/rank.

    Combines: the freelancer's ORIGINAL claimed skills (needed to detect
    overclaiming, since Member C's schema alone doesn't carry this),
    Member B's verified_skills, and Member C's matched_jobs.
    """

    candidate_id: str = Field(..., min_length=1, max_length=64)
    claimed_skills: List[str] = Field(..., min_length=1, max_length=50)
    verified_skills: List[VerifiedSkill] = Field(default_factory=list)
    matched_jobs: List[MatchedJob] = Field(default_factory=list)


class FairRankingResponse(BaseModel):
    candidate_id: str
    fairness: FairnessBreakdown
    ranked_jobs: List[FairMatchedJob]
    verified_skills: List[VerifiedSkill] = Field(
        default_factory=list,
        description=(
            "Passthrough of Member B's per-skill verification results, so the UI "
            "can render a real skills breakdown without any new backend logic."
        ),
    )


# ---- Auth ----
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ---- Integration (orchestration across A/B/C) ----
class OrchestrateRequest(BaseModel):
    """
    Request body for POST /api/orchestrate.

    Member D calls Member B's and Member C's live services on the caller's
    behalf, then applies fair ranking -- this is Member D's "Integration"
    responsibility from the brief.
    """

    candidate_id: Optional[str] = None
    claimed_skills: List[str] = Field(..., min_length=1, max_length=50)
    portfolio_evidence: dict = Field(
        ..., description="Raw response body from Member A's POST /extract-evidence"
    )
    experience_years: float = Field(default=0.0, ge=0.0)


# ---- Full pipeline (A -> B -> C -> D in one call) ----
class PortfolioProject(BaseModel):
    project_id: str
    title: str = ""
    description: str = ""
    url: Optional[str] = None
    role: Optional[str] = None


class Certificate(BaseModel):
    certificate_id: str
    title: str = ""
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    description: str = ""


class CodeSample(BaseModel):
    sample_id: str
    filename: Optional[str] = None
    language: Optional[str] = None
    snippet: str = ""


class WorkDescription(BaseModel):
    work_id: str
    description: str = ""


class FullPipelineRequest(BaseModel):
    """
    Request body for POST /api/full-pipeline.

    Mirrors Member A's ProfileRequest fields exactly (portfolio_projects,
    certificates, code_samples, work_descriptions) plus what Member B and the
    fairness layer need (claimed_skills, experience_years). This is the single
    entry point the system's UI uses: one authenticated call that walks the
    whole pipeline Agent A -> Agent B -> Agent C -> Agent D.
    """

    candidate_id: str = Field(..., min_length=1, max_length=64)
    claimed_skills: List[str] = Field(..., min_length=1, max_length=50)
    experience_years: float = Field(default=0.0, ge=0.0)

    portfolio_projects: List[PortfolioProject] = Field(default_factory=list)
    certificates: List[Certificate] = Field(default_factory=list)
    code_samples: List[CodeSample] = Field(default_factory=list)
    work_descriptions: List[WorkDescription] = Field(default_factory=list)
