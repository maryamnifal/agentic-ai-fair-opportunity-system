from typing import Dict, List, Set

from .schemas import Job, VerifiedSkill


SUPPORTED_STATUSES = {"supported", "weakly_supported"}


# Maps verified skills to the categories used by the job dataset.
# This keeps category matching inside Member C and does not require
# Member B to change its response format.
SKILL_CATEGORY_MAP: Dict[str, Set[str]] = {
    "python": {"programming", "data_analysis", "machine_learning", "backend", "data_engineering"},
    "sql": {"database", "data_analysis", "data_engineering", "business_intelligence"},
    "pandas": {"data_analysis", "data_science"},
    "numpy": {"data_analysis", "data_science", "machine_learning"},
    "scikit-learn": {"machine_learning", "data_science"},
    "sklearn": {"machine_learning", "data_science"},
    "xgboost": {"machine_learning", "data_science"},
    "machine learning": {"machine_learning", "data_science"},
    "deep learning": {"machine_learning", "data_science"},
    "tensorflow": {"machine_learning", "deep_learning"},
    "pytorch": {"machine_learning", "deep_learning"},
    "power bi": {"business_intelligence", "data_visualization"},
    "excel": {"business_intelligence", "data_analysis"},
    "tableau": {"business_intelligence", "data_visualization"},
    "matplotlib": {"data_visualization", "data_analysis"},
    "seaborn": {"data_visualization", "data_analysis"},
    "nlp": {"nlp", "machine_learning"},
    "spacy": {"nlp"},
    "transformers": {"nlp", "machine_learning"},
    "faiss": {"information_retrieval", "machine_learning"},
    "git": {"software_development"},
    "rest api": {"backend", "software_development"},
    "django": {"backend", "web_development"},
    "flask": {"backend", "web_development"},
    "fastapi": {"backend", "web_development"},
    "etl": {"data_engineering"},
    "ssis": {"data_engineering"},
    "ssas": {"business_intelligence", "data_engineering"},
}


def normalize_skill(skill: str) -> str:
    """
    Normalize skill names so matching is case-insensitive.
    """
    return skill.strip().lower()


def get_usable_skills(
    verified_skills: List[VerifiedSkill]
) -> Set[str]:
    """
    Return skills that have evidence support.

    Unsupported and contradicted skills are excluded.
    """
    return {
        normalize_skill(item.skill)
        for item in verified_skills
        if item.status in SUPPORTED_STATUSES
    }


def get_candidate_categories(
    verified_skills: List[VerifiedSkill]
) -> Set[str]:
    """
    Derive capability categories from evidence-supported skills.
    """
    categories: Set[str] = set()

    for item in verified_skills:
        if item.status not in SUPPORTED_STATUSES:
            continue

        skill = normalize_skill(item.skill)
        categories.update(SKILL_CATEGORY_MAP.get(skill, set()))

    return categories


def meets_experience_requirement(
    job: Job,
    experience_years: float
) -> bool:
    """
    Check whether the candidate satisfies the job's
    minimum experience requirement.
    """
    return experience_years >= job.minimum_experience_years


def matches_skill_category(
    job: Job,
    candidate_categories: Set[str]
) -> bool:
    """
    Check whether the candidate's capability categories
    overlap with the categories required by the job.

    Jobs without category information are not rejected.
    """
    if not job.skill_categories:
        return True

    return bool(
        candidate_categories.intersection(
            {
                category.strip().lower()
                for category in job.skill_categories
            }
        )
    )


def filter_jobs(
    jobs: List[Job],
    verified_skills: List[VerifiedSkill],
    experience_years: float
) -> List[Job]:
    """
    Structured filtering based on:

    1. Evidence-supported skills
    2. Minimum experience
    3. Skill-category compatibility

    A job is retained when:
    - the candidate satisfies the experience requirement,
    - the candidate has at least one evidence-supported
      required or preferred skill, and
    - the candidate's capability category overlaps with
      the job category.

    Jobs without category information remain eligible.
    """

    usable_skills = get_usable_skills(verified_skills)
    candidate_categories = get_candidate_categories(verified_skills)

    filtered_jobs = []

    for job in jobs:

        # Experience filter
        if not meets_experience_requirement(
            job,
            experience_years
        ):
            continue

        # Skill-category filter
        if not matches_skill_category(
            job,
            candidate_categories
        ):
            continue

        # Evidence-supported skill overlap
        job_skills = {
            normalize_skill(skill)
            for skill in (
                job.required_skills + job.preferred_skills
            )
        }

        if usable_skills.intersection(job_skills):
            filtered_jobs.append(job)

    return filtered_jobs