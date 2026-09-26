"""
Integration layer (Member D's "Integration" responsibility).

Chains the pipeline: Member B (Skill Verification Agent) -> Member C (Job
Compatibility Agent) -> this service's own fairness ranking. This is Member
D's job specifically because the brief assigns "Integration" to Member D --
Members B and C each own only their own agent's HTTP boundary.

Service URLs are configurable via environment variables so this works
whether B/C run locally on different ports, in Docker, or in CI:

  SKILL_VERIFICATION_URL   (default: http://localhost:8001)
  JOB_COMPATIBILITY_URL    (default: http://localhost:8002)

Uses plain HTTP/JSON between agents (the brief lists HTTP as an accepted
agent communication protocol alongside MCP/sockets).
"""

import os
from typing import List

import httpx

from app.schemas import VerifiedSkill, MatchedJob

SKILL_VERIFICATION_URL = os.environ.get("SKILL_VERIFICATION_URL", "http://localhost:8001")
JOB_COMPATIBILITY_URL = os.environ.get("JOB_COMPATIBILITY_URL", "http://localhost:8002")

TIMEOUT_SECONDS = 10.0


class UpstreamServiceError(Exception):
    """Raised when Member B's or Member C's service can't be reached or errors out."""

    def __init__(self, service: str, detail: str):
        self.service = service
        self.detail = detail
        super().__init__(f"{service}: {detail}")


def call_skill_verification(
    claimed_skills: List[str], portfolio_evidence: dict
) -> tuple[str, List[VerifiedSkill]]:
    """Calls Member B's POST /api/verify-skills-from-portfolio."""
    url = f"{SKILL_VERIFICATION_URL}/api/verify-skills-from-portfolio"
    payload = {"claimed_skills": claimed_skills, "portfolio_evidence": portfolio_evidence}
    try:
        resp = httpx.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    except httpx.RequestError as exc:
        raise UpstreamServiceError("skill_verification_agent", str(exc)) from exc

    if resp.status_code != 200:
        raise UpstreamServiceError(
            "skill_verification_agent", f"HTTP {resp.status_code}: {resp.text[:300]}"
        )

    body = resp.json()
    verified = [VerifiedSkill(**v) for v in body.get("verified_skills", [])]
    return body.get("candidate_id", ""), verified


def call_job_compatibility(
    candidate_id: str, verified_skills: List[VerifiedSkill], experience_years: float
) -> List[MatchedJob]:
    """Calls Member C's POST /match-jobs."""
    url = f"{JOB_COMPATIBILITY_URL}/match-jobs"
    payload = {
        "candidate_id": candidate_id,
        "verified_skills": [v.model_dump() for v in verified_skills],
        "experience_years": experience_years,
    }
    try:
        resp = httpx.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    except httpx.RequestError as exc:
        raise UpstreamServiceError("job_compatibility_agent", str(exc)) from exc

    if resp.status_code != 200:
        raise UpstreamServiceError(
            "job_compatibility_agent", f"HTTP {resp.status_code}: {resp.text[:300]}"
        )

    body = resp.json()
    return [MatchedJob(**j) for j in body.get("matched_jobs", [])]
