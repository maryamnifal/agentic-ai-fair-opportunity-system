"""
Fairness scoring for Member D's Fair Ranking Agent.

WHY THIS EXISTS
----------------
Member C's Job Compatibility Agent already EXCLUDES unsupported and
contradicted skills from its compatibility_score -- so claiming extra skills
that aren't backed by evidence doesn't directly help a candidate. But it also
doesn't HURT them: a candidate who claims 20 skills (3 supported) and one who
honestly claims 3 skills (3 supported) currently score identically for the
matching skills.

The brief's fairness principle is stronger than "ignore unsupported claims" --
it says the system should "prioritize capability supported by evidence rather
than the quantity of claims." This module makes that principle an explicit,
visible part of the ranking: candidates whose claims are mostly backed by
evidence are boosted; candidates who overclaim (many unsupported/contradicted
skills relative to what they claimed) are penalized. This is deliberately a
SEPARATE, transparent adjustment layered on top of Member C's score, not a
replacement for it -- both scores are returned so the effect is auditable.

This is a small set of explainable rules, not a model, so every number can be
justified line-by-line in a viva.
"""

from dataclasses import dataclass
from typing import List

from app.schemas import VerifiedSkill, FairnessBreakdown

SUPPORTED = "supported"
WEAK = "weakly_supported"
UNSUPPORTED = "unsupported"
CONTRADICTED = "contradicted"

# How much each verified-skill status counts toward "evidence quality".
QUALITY_WEIGHTS = {
    SUPPORTED: 1.0,
    WEAK: 0.5,
    UNSUPPORTED: 0.0,
    CONTRADICTED: 0.0,
}

# How much each status counts toward the "overclaim" signal (skills claimed
# that evidence does NOT back up -- contradictions count double, since an
# active contradiction is worse than merely unproven).
OVERCLAIM_WEIGHTS = {
    SUPPORTED: 0.0,
    WEAK: 0.0,
    UNSUPPORTED: 1.0,
    CONTRADICTED: 2.0,
}

# The fairness multiplier is clamped to this range so a single bad/good
# signal can meaningfully move rank without letting fairness overwhelm
# Member C's actual capability matching.
MULTIPLIER_MIN = 0.70
MULTIPLIER_MAX = 1.20
MULTIPLIER_SPREAD = 0.30  # how strongly quality/overclaim move the multiplier


def _normalize(skill: str) -> str:
    return skill.strip().lower()


def compute_fairness(
    claimed_skills: List[str],
    verified_skills: List[VerifiedSkill],
) -> FairnessBreakdown:
    """
    Compute the fairness multiplier for one candidate from their claimed
    skills vs. Member B's verification of those claims.
    """
    claimed_count = max(1, len(claimed_skills))

    # Only count verified_skills that correspond to something actually claimed
    # (defensive: verified_skills should already mirror claimed_skills 1:1,
    # but this keeps the module correct even if extra entries slip in).
    claimed_lower = {_normalize(s) for s in claimed_skills}
    relevant = [v for v in verified_skills if _normalize(v.skill) in claimed_lower]

    supported_count = sum(1 for v in relevant if v.status == SUPPORTED)
    weak_count = sum(1 for v in relevant if v.status == WEAK)
    unsupported_count = sum(1 for v in relevant if v.status == UNSUPPORTED)
    contradicted_count = sum(1 for v in relevant if v.status == CONTRADICTED)

    quality_points = sum(QUALITY_WEIGHTS[v.status] for v in relevant if v.status in QUALITY_WEIGHTS)
    overclaim_points = sum(OVERCLAIM_WEIGHTS[v.status] for v in relevant if v.status in OVERCLAIM_WEIGHTS)

    evidence_quality = round(quality_points / claimed_count, 4)
    overclaim_ratio = round(min(overclaim_points / claimed_count, 1.0), 4)

    raw_multiplier = 1.0 + (evidence_quality - overclaim_ratio) * MULTIPLIER_SPREAD
    multiplier = round(min(max(raw_multiplier, MULTIPLIER_MIN), MULTIPLIER_MAX), 4)

    if multiplier > 1.02:
        summary = (
            f"Boosted: {supported_count}/{claimed_count} claimed skills are evidence-supported, "
            f"with no major overclaiming detected."
        )
    elif multiplier < 0.98:
        summary = (
            f"Penalized: only {supported_count}/{claimed_count} claimed skills are supported, "
            f"and {unsupported_count + contradicted_count} claim(s) are unsupported or contradicted."
        )
    else:
        summary = "Neutral: evidence quality and overclaiming roughly balance out."

    return FairnessBreakdown(
        claimed_skill_count=len(claimed_skills),
        supported_count=supported_count,
        weakly_supported_count=weak_count,
        unsupported_count=unsupported_count,
        contradicted_count=contradicted_count,
        evidence_quality=evidence_quality,
        overclaim_ratio=overclaim_ratio,
        fairness_multiplier=multiplier,
        summary=summary,
    )


@dataclass
class RankedResult:
    fair_score: float
    fairness_note: str


def apply_fairness_to_job(compatibility_score: float, fairness: FairnessBreakdown) -> RankedResult:
    """Apply the candidate-level fairness multiplier to one job's compatibility_score."""
    fair_score = round(min(max(compatibility_score * fairness.fairness_multiplier, 0.0), 1.0), 4)

    if fairness.fairness_multiplier > 1.02:
        note = f"Raised from {compatibility_score:.2f} for strong evidence-backed claims."
    elif fairness.fairness_multiplier < 0.98:
        note = f"Lowered from {compatibility_score:.2f} due to unsupported/contradicted claims."
    else:
        note = "No fairness adjustment applied."

    return RankedResult(fair_score=fair_score, fairness_note=note)
