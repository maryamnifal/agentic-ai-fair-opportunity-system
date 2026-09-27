"""
End-to-end test for the full pipeline: Agent A -> B -> C -> D, over real
HTTP against services started with `docker-compose up`.

This is DELIBERATELY separate from each agent's own unit/API test suite
(those run in isolation with mocks and don't need Docker). This file is the
"does the whole system actually work together" check.

Run:
    docker-compose up -d --build
    # wait for all services to report healthy, e.g.:
    docker-compose ps
    pytest tests/e2e -v

If the services aren't reachable, tests are skipped (not failed) so the rest
of the repo's test suites still run cleanly in CI without Docker.
"""

import uuid

import httpx
import pytest

PORTFOLIO_EVIDENCE_URL = "http://localhost:8000"
SKILL_VERIFICATION_URL = "http://localhost:8001"
JOB_COMPATIBILITY_URL = "http://localhost:8002"
FAIR_RANKING_URL = "http://localhost:8003"

ALL_SERVICES = {
    "portfolio_evidence_agent": PORTFOLIO_EVIDENCE_URL,
    "skill_verification_agent": SKILL_VERIFICATION_URL,
    "job_compatibility_agent": JOB_COMPATIBILITY_URL,
    "fair_ranking_agent": FAIR_RANKING_URL,
}


def _all_services_up() -> bool:
    for url in ALL_SERVICES.values():
        try:
            resp = httpx.get(f"{url}/health", timeout=3.0)
            if resp.status_code != 200:
                return False
        except httpx.RequestError:
            return False
    return True


requires_all_services = pytest.mark.skipif(
    not _all_services_up(),
    reason=(
        "Not all 4 agent services are reachable. Run `docker-compose up -d --build` "
        "(and wait for them to become healthy) before running tests/e2e."
    ),
)


@requires_all_services
def test_each_agent_health_check():
    for name, url in ALL_SERVICES.items():
        resp = httpx.get(f"{url}/health", timeout=5.0)
        assert resp.status_code == 200, f"{name} health check failed"


@requires_all_services
def test_agent_a_extracts_evidence_directly():
    """Sanity check on Agent A in isolation before testing the full chain."""
    payload = {
        "freelancer_id": "e2e_test_001",
        "portfolio_projects": [
            {
                "project_id": "proj_001",
                "title": "Online Booking System",
                "description": "Built a web-based booking platform using Django and REST APIs.",
            }
        ],
        "certificates": [],
        "code_samples": [],
        "work_descriptions": [],
    }
    resp = httpx.post(f"{PORTFOLIO_EVIDENCE_URL}/extract-evidence", json=payload, timeout=30.0)
    assert resp.status_code == 200
    body = resp.json()
    assert body["freelancer_id"] == "e2e_test_001"
    assert len(body["evidence_items"]) > 0


@requires_all_services
def test_full_pipeline_end_to_end():
    """
    The real end-to-end check: UI -> Agent D -> Agent A -> Agent B -> Agent C
    -> Agent D (fair ranking) -> response, using Agent D's single
    POST /api/full-pipeline entry point (exactly what the UI calls).
    """
    username = f"e2e_user_{uuid.uuid4().hex[:8]}"
    password = "e2e_test_password_123"

    # 1. Register + log in against Agent D
    reg = httpx.post(
        f"{FAIR_RANKING_URL}/auth/register",
        json={"username": username, "password": password},
        timeout=10.0,
    )
    assert reg.status_code == 201

    login = httpx.post(
        f"{FAIR_RANKING_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=10.0,
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Run the full pipeline: A -> B -> C -> D, one call
    payload = {
        "candidate_id": "e2e_candidate_001",
        "claimed_skills": ["Python", "Django", "REST API", "Machine Learning"],
        "experience_years": 2.0,
        "portfolio_projects": [
            {
                "project_id": "proj_001",
                "title": "Online Booking System",
                "description": "Built a web-based booking platform using Django and REST APIs.",
            }
        ],
        "certificates": [],
        "code_samples": [],
        "work_descriptions": [],
    }
    resp = httpx.post(
        f"{FAIR_RANKING_URL}/api/full-pipeline", json=payload, headers=headers, timeout=60.0
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["candidate_id"] == "e2e_candidate_001"
    assert "fairness" in body
    assert "ranked_jobs" in body

    # Python and Django should be evidence-supported given the portfolio text;
    # Machine Learning has no supporting evidence in this payload -> should
    # pull the fairness multiplier down somewhat (an overclaim signal).
    f = body["fairness"]
    assert f["claimed_skill_count"] == 4
    assert f["supported_count"] >= 1


@requires_all_services
def test_full_pipeline_rejects_unauthenticated_request():
    resp = httpx.post(
        f"{FAIR_RANKING_URL}/api/full-pipeline",
        json={"candidate_id": "x", "claimed_skills": ["Python"]},
        timeout=10.0,
    )
    assert resp.status_code == 401
