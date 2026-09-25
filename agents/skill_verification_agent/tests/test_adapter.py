import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.portfolio_evidence_adapter import (
    adapt_portfolio_evidence,
    adapt_candidate_id,
)

# A realistic Member A response, shaped exactly like her
# agents/portfolio_evidence_agent/agent/portfolio_evidence_agent.py `process()`
# output (see the group repo). Two skills found in the SAME project.
MEMBER_A_RESPONSE = {
    "freelancer_id": "fl_001",
    "agent": "portfolio_evidence_agent",
    "agent_version": "1.0.0",
    "extracted_at": "2026-09-25T10:00:00+00:00",
    "evidence_items": [
        {
            "skill": "Django",
            "skill_category": "web_framework",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "developed a backend application using Django and REST API",
            "extraction_method": "both",
            "confidence": 0.98,
            "reasoning": "Confirmed by both rule-based extraction and LLM interpretation.",
            "evidence_id": "ev_001",
        },
        {
            "skill": "REST API",
            "skill_category": "backend_concept",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "using Django and REST API technologies",
            "extraction_method": "ner",
            "confidence": 0.95,
            "reasoning": "Explicit mention of REST API in portfolio_project.",
            "evidence_id": "ev_002",
        },
        {
            "skill": "PostgreSQL",
            "skill_category": "database",
            "source_type": "certificate",
            "source_ref": "cert_001",
            "source_excerpt": "Certified PostgreSQL database administrator",
            "extraction_method": "ner",
            "confidence": 0.95,
            "reasoning": "Explicit mention of PostgreSQL in certificate.",
            "evidence_id": "ev_003",
        },
    ],
    "unmapped_terms": [],
    "processing_notes": [],
}


def test_adapt_candidate_id():
    assert adapt_candidate_id(MEMBER_A_RESPONSE) == "fl_001"


def test_adapt_candidate_id_missing_field():
    assert adapt_candidate_id({}) == ""


def test_groups_evidence_by_source():
    evidence = adapt_portfolio_evidence(MEMBER_A_RESPONSE)
    # Two distinct sources (proj_001, cert_001) -> two EvidenceItems, not three.
    assert len(evidence) == 2


def test_skills_from_same_source_are_grouped_together():
    evidence = adapt_portfolio_evidence(MEMBER_A_RESPONSE)
    proj_item = next(e for e in evidence if e.evidence_id == "proj_001")
    assert set(proj_item.extracted_skills) == {"Django", "REST API"}
    assert "Django" in proj_item.description
    assert "REST API" in proj_item.description


def test_certificate_source_kept_separate():
    evidence = adapt_portfolio_evidence(MEMBER_A_RESPONSE)
    cert_item = next(e for e in evidence if e.evidence_id == "cert_001")
    assert cert_item.extracted_skills == ["PostgreSQL"]
    assert cert_item.project == "certificate:cert_001"


def test_empty_evidence_items_produces_empty_list():
    result = adapt_portfolio_evidence({"freelancer_id": "fl_002", "evidence_items": []})
    assert result == []


def test_end_to_end_via_api(client):
    payload = {
        "claimed_skills": ["Python", "Django", "REST API", "MySQL"],
        "portfolio_evidence": MEMBER_A_RESPONSE,
    }
    resp = client.post("/api/verify-skills-from-portfolio", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == "fl_001"

    statuses = {v["skill"]: v["status"] for v in body["verified_skills"]}
    assert statuses["Django"] == "supported"
    assert statuses["REST API"] == "supported"
    # Python is implied (not exact) via Django in the same project -> still supported
    assert statuses["Python"] == "supported"
    # MySQL never appears in her evidence at all -> unsupported
    assert statuses["MySQL"] == "unsupported"


def test_candidate_id_override_via_api(client):
    payload = {
        "candidate_id": "OVERRIDE_ID",
        "claimed_skills": ["Django"],
        "portfolio_evidence": MEMBER_A_RESPONSE,
    }
    resp = client.post("/api/verify-skills-from-portfolio", json=payload)
    assert resp.status_code == 200
    assert resp.json()["candidate_id"] == "OVERRIDE_ID"


def test_missing_candidate_id_returns_400(client):
    payload = {
        "claimed_skills": ["Django"],
        "portfolio_evidence": {"evidence_items": []},  # no freelancer_id
    }
    resp = client.post("/api/verify-skills-from-portfolio", json=payload)
    assert resp.status_code == 400
