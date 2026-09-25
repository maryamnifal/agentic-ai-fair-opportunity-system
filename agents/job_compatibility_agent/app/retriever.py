from pathlib import Path
import json
from typing import List, Tuple

import faiss
import numpy as np

from .embeddings import EmbeddingModel
from .schemas import Job


class JobRetriever:
    """
    Semantic job retrieval using FAISS.

    Jobs are embedded once and stored in a FAISS index.
    Candidate capability text is embedded during retrieval.
    """

    def __init__(
        self,
        jobs_path: str,
        embedding_model: EmbeddingModel | None = None
    ):
        self.jobs_path = Path(jobs_path)
        self.embedding_model = embedding_model or EmbeddingModel()

        self.jobs = self._load_jobs()
        self.index = self._build_index()

    def _load_jobs(self) -> List[Job]:
        with self.jobs_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return [Job(**job) for job in data]

    def _job_text(self, job: Job) -> str:
        """
        Combine important job information into one searchable text.
        """

        return " ".join(
            [
                job.title,
                job.description,
                "Required skills: " + ", ".join(job.required_skills),
                "Preferred skills: " + ", ".join(job.preferred_skills),
                "Categories: " + ", ".join(job.skill_categories),
            ]
        )

    def _build_index(self) -> faiss.Index:
        """
        Build a FAISS inner-product index.

        Because embeddings are normalized, inner product is equivalent
        to cosine similarity.
        """

        job_texts = [self._job_text(job) for job in self.jobs]

        embeddings = self.embedding_model.encode(job_texts)

        dimension = embeddings.shape[1]

        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        return index

    def retrieve(
        self,
        candidate_text: str,
        top_k: int = 10
    ) -> List[Tuple[Job, float]]:
        """
        Retrieve the most semantically similar jobs.
        """

        candidate_embedding = self.embedding_model.encode(
            [candidate_text]
        )

        scores, indices = self.index.search(
            candidate_embedding,
            min(top_k, len(self.jobs))
        )

        results = []

        for score, index in zip(scores[0], indices[0]):
            if index == -1:
                continue

            results.append(
                (
                    self.jobs[index],
                    float(score)
                )
            )

        return results