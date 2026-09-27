import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import VerifiedSkill, MatchedJob, FairRankingRequest
from app.ranking_agent import FairRankingAgent


def test_reranks_by_fair_score():
    agent = FairRankingAgent()
    request = FairRankingRequest(
        candidate_id="F001",
        claimed_skills=["Python", "Java", "React"],
        verified_skills=[
            VerifiedSkill(skill="Python", status="supported", confidence=0.9),
            VerifiedSkill(skill="Java", status="unsupported", confidence=0.05),
            VerifiedSkill(skill="React", status="unsupported", confidence=0.05),
        ],
        matched_jobs=[
            MatchedJob(job_id="J1", title="Backend Dev", compatibility_score=0.6,
                       semantic_score=0.6, structured_score=0.6),
            MatchedJob(job_id="J2", title="Frontend Dev", compatibility_score=0.65,
                       semantic_score=0.65, structured_score=0.65),
        ],
    )
    result = agent.rank(request)
    assert len(result.ranked_jobs) == 2
    # fair_rank should be a valid permutation of 1..N
    assert sorted(j.fair_rank for j in result.ranked_jobs) == [1, 2]
    # ranked_jobs should be sorted by fair_score descending
    scores = [j.fair_score for j in result.ranked_jobs]
    assert scores == sorted(scores, reverse=True)


def test_original_rank_preserved_from_input_order():
    agent = FairRankingAgent()
    request = FairRankingRequest(
        candidate_id="F002",
        claimed_skills=["Python"],
        verified_skills=[VerifiedSkill(skill="Python", status="supported", confidence=0.9)],
        matched_jobs=[
            MatchedJob(job_id="J1", title="A", compatibility_score=0.9, semantic_score=0.9, structured_score=0.9),
            MatchedJob(job_id="J2", title="B", compatibility_score=0.7, semantic_score=0.7, structured_score=0.7),
        ],
    )
    result = agent.rank(request)
    original_ranks = {j.job_id: j.original_rank for j in result.ranked_jobs}
    assert original_ranks["J1"] == 1
    assert original_ranks["J2"] == 2


def test_empty_matched_jobs_returns_empty_ranked_list():
    agent = FairRankingAgent()
    request = FairRankingRequest(
        candidate_id="F003",
        claimed_skills=["Python"],
        verified_skills=[VerifiedSkill(skill="Python", status="supported", confidence=0.9)],
        matched_jobs=[],
    )
    result = agent.rank(request)
    assert result.ranked_jobs == []


def test_response_includes_verified_skills_passthrough():
    """Regression: verified_skills must be returned so the UI can show a real skills breakdown."""
    agent = FairRankingAgent()
    verified = [
        VerifiedSkill(skill="Python", status="supported", confidence=0.9),
        VerifiedSkill(skill="React", status="unsupported", confidence=0.05),
    ]
    request = FairRankingRequest(
        candidate_id="F004",
        claimed_skills=["Python", "React"],
        verified_skills=verified,
        matched_jobs=[],
    )
    result = agent.rank(request)
    assert len(result.verified_skills) == 2
    assert result.verified_skills[0].skill == "Python"
    assert result.verified_skills[0].confidence == 0.9
