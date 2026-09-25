"""
Pydantic schemas for the Skill Verification Agent (Member B).

These are treated as a PROPOSED contract with Member A (evidence producer)
and Member C (consumer of verified skills). Field names/types can be
adjusted here in one place if the group agrees on a different final schema.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# ---- Limits used by validation.py too (kept here so schema + validator agree) ----
MAX_CANDIDATE_ID_LEN = 64
MAX_SKILL_LEN = 60
MAX_SKILLS = 30
MAX_DESCRIPTION_LEN = 2000
MAX_PROJECT_NAME_LEN = 120
MAX_EVIDENCE_ITEMS = 30
MAX_EXTRACTED_SKILLS = 30


class EvidenceItem(BaseModel):
    """One structured evidence object, as produced by Member A's Portfolio Evidence Agent."""

    evidence_id: str = Field(..., min_length=1, max_length=MAX_CANDIDATE_ID_LEN)
    project: str = Field(..., min_length=1, max_length=MAX_PROJECT_NAME_LEN)
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LEN)
    extracted_skills: List[str] = Field(default_factory=list, max_length=MAX_EXTRACTED_SKILLS)

    @field_validator("extracted_skills")
    @classmethod
    def _strip_skills(cls, v: List[str]) -> List[str]:
        return [s.strip() for s in v if s and s.strip()]


class VerifyRequest(BaseModel):
    """Request body for POST /api/verify-skills."""

    candidate_id: str = Field(..., min_length=1, max_length=MAX_CANDIDATE_ID_LEN)
    claimed_skills: List[str] = Field(..., min_length=1, max_length=MAX_SKILLS)
    evidence: List[EvidenceItem] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)

    @field_validator("claimed_skills")
    @classmethod
    def _clean_claimed_skills(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("claimed_skills must contain at least one non-empty skill")
        for s in cleaned:
            if len(s) > MAX_SKILL_LEN:
                raise ValueError(f"skill '{s[:20]}...' exceeds max length of {MAX_SKILL_LEN}")
        return cleaned


class VerifiedSkill(BaseModel):
    """Result for a single claimed skill."""

    skill: str
    status: str  # "supported" | "weakly_supported" | "unsupported" | "contradicted"
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str


class ResponseMeta(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_version: str = "1.0"
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duplicate_skills_removed: List[str] = Field(default_factory=list)


class VerifyResponse(BaseModel):
    """Response body for POST /api/verify-skills. This is what Member C consumes."""

    candidate_id: str
    verified_skills: List[VerifiedSkill]
    meta: ResponseMeta


class ErrorResponse(BaseModel):
    """Standard error shape returned on validation/processing failure."""

    error: str
    detail: Optional[str] = None


class PortfolioEvidenceVerifyRequest(BaseModel):
    """
    Request body for POST /api/verify-skills-from-portfolio.

    This accepts Member A's Portfolio Evidence Agent output DIRECTLY (the raw
    dict her /extract-evidence endpoint returns), so Member C/D can chain the
    two agents without writing their own conversion code. See
    app/adapters/portfolio_evidence_adapter.py for the shape this expects.
    """

    candidate_id: Optional[str] = Field(
        default=None,
        max_length=MAX_CANDIDATE_ID_LEN,
        description="Optional override; if omitted, taken from portfolio_evidence.freelancer_id",
    )
    claimed_skills: List[str] = Field(..., min_length=1, max_length=MAX_SKILLS)
    portfolio_evidence: dict = Field(
        ..., description="Raw response body from Member A's POST /extract-evidence"
    )
