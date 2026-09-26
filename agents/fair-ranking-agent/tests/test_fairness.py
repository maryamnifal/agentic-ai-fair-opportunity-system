import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import VerifiedSkill
from app.fairness import compute_fairness, apply_fairness_to_job


def test_honest_candidate_gets_boosted():
    fairness = compute_fairness(
        ["Python", "Django", "REST API"],
        [
            VerifiedSkill(skill="Python", status="supported", confidence=0.9),
            VerifiedSkill(skill="Django", status="supported", confidence=0.97),
            VerifiedSkill(skill="REST API", status="supported", confidence=0.9),
        ],
    )
    assert fairness.fairness_multiplier > 1.0
    assert fairness.overclaim_ratio == 0.0


def test_overclaiming_candidate_gets_penalized():
    fairness = compute_fairness(
        ["Python", "Java", "React", "ML"],
        [
            VerifiedSkill(skill="Python", status="supported", confidence=0.9),
            VerifiedSkill(skill="Java", status="contradicted", confidence=0.02),
            VerifiedSkill(skill="React", status="unsupported", confidence=0.05),
            VerifiedSkill(skill="ML", status="unsupported", confidence=0.05),
        ],
    )
    assert fairness.fairness_multiplier < 1.0
    assert fairness.unsupported_count == 2
    assert fairness.contradicted_count == 1


def test_multiplier_is_clamped():
    # All contradicted -> should not go below MULTIPLIER_MIN
    fairness = compute_fairness(
        ["A", "B"],
        [
            VerifiedSkill(skill="A", status="contradicted", confidence=0.0),
            VerifiedSkill(skill="B", status="contradicted", confidence=0.0),
        ],
    )
    assert fairness.fairness_multiplier >= 0.70


def test_apply_fairness_to_job_boost():
    fairness = compute_fairness(
        ["Python"], [VerifiedSkill(skill="Python", status="supported", confidence=0.9)]
    )
    result = apply_fairness_to_job(0.5, fairness)
    assert result.fair_score > 0.5


def test_apply_fairness_to_job_penalty():
    fairness = compute_fairness(
        ["Python"], [VerifiedSkill(skill="Python", status="contradicted", confidence=0.0)]
    )
    result = apply_fairness_to_job(0.5, fairness)
    assert result.fair_score < 0.5


def test_two_candidates_same_raw_score_different_fair_score():
    """The core fairness claim: same compatibility_score, different fair_score."""
    honest = compute_fairness(
        ["Python", "Django"],
        [
            VerifiedSkill(skill="Python", status="supported", confidence=0.9),
            VerifiedSkill(skill="Django", status="supported", confidence=0.9),
        ],
    )
    overclaimer = compute_fairness(
        ["Python", "Django", "Java", "React", "ML", "AWS"],
        [
            VerifiedSkill(skill="Python", status="supported", confidence=0.9),
            VerifiedSkill(skill="Django", status="supported", confidence=0.9),
            VerifiedSkill(skill="Java", status="unsupported", confidence=0.05),
            VerifiedSkill(skill="React", status="unsupported", confidence=0.05),
            VerifiedSkill(skill="ML", status="unsupported", confidence=0.05),
            VerifiedSkill(skill="AWS", status="unsupported", confidence=0.05),
        ],
    )
    honest_result = apply_fairness_to_job(0.8, honest)
    overclaimer_result = apply_fairness_to_job(0.8, overclaimer)
    assert honest_result.fair_score > overclaimer_result.fair_score
