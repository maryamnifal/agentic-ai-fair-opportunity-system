"""
FairRankingAgent: takes Member C's matched_jobs plus the candidate's original
claims and Member B's verification of them, and produces a fairness-adjusted
re-ranking.

No HTTP concerns here (see main.py / integration.py) -- this can be unit
tested directly.
"""

from typing import List

from app.schemas import (
    FairRankingRequest,
    FairRankingResponse,
    FairMatchedJob,
)
from app.fairness import compute_fairness, apply_fairness_to_job


class FairRankingAgent:
    def rank(self, request: FairRankingRequest) -> FairRankingResponse:
        fairness = compute_fairness(request.claimed_skills, request.verified_skills)

        # Member C already sorts matched_jobs by compatibility_score descending;
        # record that original order before we re-rank.
        original_order = list(request.matched_jobs)

        fair_jobs: List[FairMatchedJob] = []
        for original_rank, job in enumerate(original_order, start=1):
            result = apply_fairness_to_job(job.compatibility_score, fairness)
            fair_jobs.append(
                FairMatchedJob(
                    job_id=job.job_id,
                    title=job.title,
                    compatibility_score=job.compatibility_score,
                    fair_score=result.fair_score,
                    original_rank=original_rank,
                    fair_rank=0,  # filled in after sort
                    matched_skills=job.matched_skills,
                    missing_skills=job.missing_skills,
                    explanation=job.explanation,
                    fairness_note=result.fairness_note,
                )
            )

        fair_jobs.sort(key=lambda j: j.fair_score, reverse=True)
        for fair_rank, job in enumerate(fair_jobs, start=1):
            job.fair_rank = fair_rank

        return FairRankingResponse(
            candidate_id=request.candidate_id,
            fairness=fairness,
            ranked_jobs=fair_jobs,
            verified_skills=request.verified_skills,
        )
