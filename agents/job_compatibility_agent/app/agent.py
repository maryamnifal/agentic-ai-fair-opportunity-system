from pathlib import Path
from typing import List

from .filters import filter_jobs
from .matcher import match_job
from .retriever import JobRetriever
from .schemas import (
    CandidateProfile,
    JobCompatibilityResponse,
    MatchedJob,
)


class JobCompatibilityAgent:
    """
    Member C's Job Compatibility Agent.

    Pipeline:

    Candidate verified skills
            ↓
    Semantic retrieval
            ↓
    Structured filtering
            ↓
    Hybrid compatibility scoring
            ↓
    Explainable job matches
    """

    def __init__(self, jobs_path: str | None = None):

        if jobs_path is None:
            jobs_path = str(
                Path(__file__).resolve().parent.parent
                / "data"
                / "jobs.json"
            )

        self.retriever = JobRetriever(jobs_path)

    def _candidate_text(
        self,
        candidate: CandidateProfile
    ) -> str:

        skills = [
            item.skill
            for item in candidate.verified_skills
            if item.status in {
                "supported",
                "weakly_supported"
            }
        ]

        return (
            "Candidate capabilities: "
            + ", ".join(skills)
        )

    def match_jobs(
        self,
        candidate: CandidateProfile,
        top_k: int = 5
    ) -> JobCompatibilityResponse:

        candidate_text = self._candidate_text(candidate)

        semantic_results = self.retriever.retrieve(
            candidate_text,
            top_k=10
        )

        retrieved_jobs = [
            job
            for job, _ in semantic_results
        ]

        structured_jobs = filter_jobs(
            retrieved_jobs,
            candidate.verified_skills,
            candidate.experience_years
        )

        structured_job_ids = {
            job.job_id
            for job in structured_jobs
        }

        matches: List[MatchedJob] = []

        for job, semantic_score in semantic_results:

            if job.job_id not in structured_job_ids:
                continue

            result = match_job(
                job,
                semantic_score,
                candidate.verified_skills
            )

            matches.append(result)

        matches.sort(
            key=lambda item: item.compatibility_score,
            reverse=True
        )

        return JobCompatibilityResponse(
            candidate_id=candidate.candidate_id,
            matched_jobs=matches[:top_k]
        )