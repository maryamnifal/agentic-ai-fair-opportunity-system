from agents.job_compatibility_agent.app.matcher import (
    calculate_hybrid_score,
    calculate_structured_score,
)
from agents.job_compatibility_agent.app.schemas import (
    Job,
    VerifiedSkill,
)


def test_hybrid_score():

    score = calculate_hybrid_score(
        semantic_score=0.8,
        structured_score=0.6,
    )

    assert score == 0.72


def test_structured_score_with_matching_skills():

    job = Job(
        job_id="JOB001",
        title="Data Analyst",
        description="Analyze data",
        required_skills=["Python", "SQL"],
        preferred_skills=["Pandas"],
        skill_categories=["data_analysis"],
        minimum_experience_years=0,
    )

    skills = [
        VerifiedSkill(
            skill="Python",
            status="supported",
            confidence=1.0,
        ),
        VerifiedSkill(
            skill="SQL",
            status="supported",
            confidence=0.8,
        ),
        VerifiedSkill(
            skill="Pandas",
            status="supported",
            confidence=0.9,
        ),
    ]

    score, matched, missing = calculate_structured_score(
        job,
        skills,
    )

    assert score > 0
    assert "Python" in matched
    assert "SQL" in matched
    assert "Pandas" in matched
    assert missing == []