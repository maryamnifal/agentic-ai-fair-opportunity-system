from typing import List

from .filters import normalize_skill
from .schemas import Job, MatchedJob, VerifiedSkill


SEMANTIC_WEIGHT = 0.60
STRUCTURED_WEIGHT = 0.40


def calculate_structured_score(
    job: Job,
    verified_skills: List[VerifiedSkill]
) -> tuple[float, List[str], List[str]]:
    """
    Calculate capability-based structured compatibility.

    The score considers:

    - required skill coverage
    - verification confidence from Member B
    - preferred skill coverage
    """

    verified_map = {
        normalize_skill(item.skill): item
        for item in verified_skills
        if item.status in {"supported", "weakly_supported"}
    }

    required_scores = []
    matched_skills = []
    missing_skills = []

    for required_skill in job.required_skills:

        normalized = normalize_skill(required_skill)

        if normalized in verified_map:
            item = verified_map[normalized]

            required_scores.append(item.confidence)
            matched_skills.append(required_skill)

        else:
            required_scores.append(0.0)
            missing_skills.append(required_skill)

    preferred_scores = []

    for preferred_skill in job.preferred_skills:

        normalized = normalize_skill(preferred_skill)

        if normalized in verified_map:
            preferred_scores.append(
                verified_map[normalized].confidence
            )
            matched_skills.append(preferred_skill)

    required_score = (
        sum(required_scores) / len(required_scores)
        if required_scores
        else 0.0
    )

    preferred_score = (
        sum(preferred_scores) / len(preferred_scores)
        if preferred_scores
        else 0.0
    )

    structured_score = (
        0.75 * required_score
        + 0.25 * preferred_score
    )

    return (
        min(structured_score, 1.0),
        sorted(set(matched_skills)),
        sorted(set(missing_skills))
    )


def calculate_hybrid_score(
    semantic_score: float,
    structured_score: float
) -> float:
    """
    Combine semantic and structured compatibility.

    60% semantic similarity
    40% evidence-supported structured matching
    """

    score = (
        SEMANTIC_WEIGHT * semantic_score
        + STRUCTURED_WEIGHT * structured_score
    )

    return round(min(max(score, 0.0), 1.0), 4)


def build_explanation(
    job: Job,
    semantic_score: float,
    structured_score: float,
    matched_skills: List[str],
    missing_skills: List[str]
) -> str:

    matched_text = (
        ", ".join(matched_skills)
        if matched_skills
        else "none"
    )

    missing_text = (
        ", ".join(missing_skills)
        if missing_skills
        else "none"
    )

    return (
        f"Semantic similarity: {semantic_score:.2f}. "
        f"Evidence-supported structured score: "
        f"{structured_score:.2f}. "
        f"Matched skills: {matched_text}. "
        f"Missing required skills: {missing_text}."
    )


def match_job(
    job: Job,
    semantic_score: float,
    verified_skills: List[VerifiedSkill]
) -> MatchedJob:

    structured_score, matched_skills, missing_skills = (
        calculate_structured_score(
            job,
            verified_skills
        )
    )

    compatibility_score = calculate_hybrid_score(
        semantic_score,
        structured_score
    )

    explanation = build_explanation(
        job,
        semantic_score,
        structured_score,
        matched_skills,
        missing_skills
    )

    return MatchedJob(
        job_id=job.job_id,
        title=job.title,
        compatibility_score=compatibility_score,
        semantic_score=round(semantic_score, 4),
        structured_score=round(structured_score, 4),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        explanation=explanation
    )