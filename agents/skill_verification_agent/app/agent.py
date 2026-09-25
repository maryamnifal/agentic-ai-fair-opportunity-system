"""
SkillVerificationAgent: orchestrates matching for a full request.

This is the single entry point Member D's integration layer (or a test)
should call. It intentionally has no FastAPI/HTTP concerns -- those live
in main.py -- so it can be unit tested directly and reused if the
transport layer ever changes.
"""

from typing import List

from app.schemas import VerifyRequest, VerifyResponse, VerifiedSkill, ResponseMeta
from app.matching import score_skill_against_evidence


class SkillVerificationAgent:
    """
    Evaluates claim-evidence consistency for a candidate.

    NOTE: this agent does NOT verify identity, credentials, or real-world
    competence. It only reports whether a claimed skill is supported by the
    portfolio evidence supplied to it.
    """

    def verify(self, request: VerifyRequest) -> VerifyResponse:
        claimed = request.claimed_skills

        # De-duplicate claimed skills case-insensitively, preserving first-seen casing.
        seen_lower = set()
        deduped: List[str] = []
        removed: List[str] = []
        for skill in claimed:
            key = skill.strip().lower()
            if key in seen_lower:
                removed.append(skill)
                continue
            seen_lower.add(key)
            deduped.append(skill.strip())

        verified: List[VerifiedSkill] = []
        for skill in deduped:
            verdict = score_skill_against_evidence(skill, request.evidence)
            verified.append(
                VerifiedSkill(
                    skill=verdict.skill,
                    status=verdict.status,
                    confidence=verdict.confidence,
                    evidence_ids=verdict.evidence_ids,
                    reason=verdict.reason,
                )
            )

        return VerifyResponse(
            candidate_id=request.candidate_id,
            verified_skills=verified,
            meta=ResponseMeta(duplicate_skills_removed=removed),
        )
