import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import EvidenceItem
from app.matching import score_skill_against_evidence, STATUS_SUPPORTED, STATUS_WEAK, \
    STATUS_UNSUPPORTED, STATUS_CONTRADICTED


def make_evidence(**kwargs):
    defaults = dict(evidence_id="E001", project="Test Project", description="", extracted_skills=[])
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


# 1. Strong / exact match
def test_exact_match_supported():
    ev = make_evidence(
        description="Built a Django REST API for bookings.",
        extracted_skills=["Python", "Django", "REST API"],
    )
    verdict = score_skill_against_evidence("Django", [ev])
    assert verdict.status == STATUS_SUPPORTED
    assert verdict.confidence >= 0.9
    assert "E001" in verdict.evidence_ids


# 2. Strong implied match (framework implies language)
def test_implied_match_supported():
    ev = make_evidence(
        description="Developed a Django application.",
        extracted_skills=["Django"],
    )
    verdict = score_skill_against_evidence("Python", [ev])
    assert verdict.status == STATUS_SUPPORTED
    assert 0.6 <= verdict.confidence < 0.9


# 3. Weak match
def test_weak_related_match():
    ev = make_evidence(
        description="Performed data analysis using Pandas.",
        extracted_skills=["Pandas", "Data Analysis"],
    )
    verdict = score_skill_against_evidence("Machine Learning", [ev])
    assert verdict.status == STATUS_WEAK
    assert 0.2 <= verdict.confidence < 0.6


# 4. No evidence / unsupported
def test_no_evidence_unsupported():
    ev = make_evidence(
        description="Built a Java Spring Boot backend.",
        extracted_skills=["Java", "Spring Boot"],
    )
    verdict = score_skill_against_evidence("React", [ev])
    assert verdict.status == STATUS_UNSUPPORTED
    assert verdict.evidence_ids == []


# 5. Empty evidence list entirely
def test_empty_evidence_list():
    verdict = score_skill_against_evidence("Python", [])
    assert verdict.status == STATUS_UNSUPPORTED
    assert verdict.confidence < 0.2


# 6. Contradictory evidence
def test_contradiction_detected():
    ev = make_evidence(
        description="Built entirely in Java using Spring Boot with no use of Python.",
        extracted_skills=["Java", "Spring Boot"],
    )
    verdict = score_skill_against_evidence("Python", [ev])
    assert verdict.status == STATUS_CONTRADICTED
    assert verdict.confidence < 0.1


# 7. Multiple evidence items -- best match wins, ids aggregate
def test_multiple_supporting_evidence_items():
    ev1 = make_evidence(evidence_id="E010", description="ETL scripts.", extracted_skills=["Python"])
    ev2 = make_evidence(evidence_id="E011", description="Flask backend.", extracted_skills=["Flask", "Python"])
    verdict = score_skill_against_evidence("Python", [ev1, ev2])
    assert verdict.status == STATUS_SUPPORTED
    assert set(verdict.evidence_ids) == {"E010", "E011"}


# 8. Unrelated skill in same portfolio should not be assumed supported
def test_does_not_assume_unrelated_skill_from_same_portfolio():
    ev = make_evidence(
        description="Static HTML/CSS website.",
        extracted_skills=["HTML", "CSS"],
    )
    verdict = score_skill_against_evidence("Machine Learning", [ev])
    assert verdict.status == STATUS_UNSUPPORTED


# 9. Regression: substring false positive (Java should NOT match JavaScript)
def test_java_does_not_match_javascript_substring():
    ev = make_evidence(
        description="Built a JavaScript frontend.",
        extracted_skills=["JavaScript"],
    )
    verdict = score_skill_against_evidence("Java", [ev])
    assert verdict.status == STATUS_UNSUPPORTED


# 10. Regression: contradiction retains the evidence_id that caused it
def test_contradiction_retains_evidence_id():
    ev = make_evidence(
        evidence_id="E005",
        description="Built entirely in Java using Spring Boot with no use of Python.",
        extracted_skills=["Java", "Spring Boot"],
    )
    verdict = score_skill_against_evidence("Python", [ev])
    assert verdict.status == STATUS_CONTRADICTED
    assert "E005" in verdict.evidence_ids


# 11. Regression: alias "JS" should be treated as an exact match for "JavaScript"
def test_alias_js_matches_javascript():
    ev = make_evidence(
        description="Built a React app in JavaScript.",
        extracted_skills=["JavaScript"],
    )
    verdict = score_skill_against_evidence("JS", [ev])
    assert verdict.status == STATUS_SUPPORTED
    assert verdict.confidence >= 0.9
