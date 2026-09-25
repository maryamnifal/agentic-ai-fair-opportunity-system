import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import VerifyRequest, EvidenceItem
from app.agent import SkillVerificationAgent


def test_agent_full_request_multiple_skills():
    agent = SkillVerificationAgent()
    request = VerifyRequest(
        candidate_id="F001",
        claimed_skills=["Python", "Django", "Machine Learning", "React"],
        evidence=[
            EvidenceItem(
                evidence_id="E001",
                project="Online Booking System",
                description="Built a web-based booking platform using Django and REST APIs.",
                extracted_skills=["Python", "Django", "REST API", "Web Development"],
            )
        ],
    )
    result = agent.verify(request)
    statuses = {v.skill: v.status for v in result.verified_skills}
    assert statuses["Python"] == "supported"
    assert statuses["Django"] == "supported"
    assert statuses["Machine Learning"] == "unsupported"
    assert statuses["React"] == "unsupported"


def test_agent_deduplicates_case_insensitive_skills():
    agent = SkillVerificationAgent()
    request = VerifyRequest(
        candidate_id="F012",
        claimed_skills=["Python", "python", "PYTHON", "Django"],
        evidence=[
            EvidenceItem(
                evidence_id="E012",
                project="Blog Platform",
                description="Developed a blogging platform with Django.",
                extracted_skills=["Python", "Django"],
            )
        ],
    )
    result = agent.verify(request)
    skill_names = [v.skill.lower() for v in result.verified_skills]
    assert skill_names.count("python") == 1
    assert len(result.meta.duplicate_skills_removed) == 2
