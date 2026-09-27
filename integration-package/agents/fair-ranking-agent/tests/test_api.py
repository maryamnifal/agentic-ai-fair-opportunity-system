from unittest.mock import patch

from app.schemas import VerifiedSkill, MatchedJob


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_rank_missing_required_field_returns_422(client, auth_headers):
    resp = client.post("/api/rank", json={"candidate_id": "F001"}, headers=auth_headers)
    assert resp.status_code == 422


def test_rank_full_flow(client, auth_headers):
    payload = {
        "candidate_id": "F001",
        "claimed_skills": ["Python", "Django"],
        "verified_skills": [
            {"skill": "Python", "status": "supported", "confidence": 0.9, "evidence_ids": [], "reason": ""},
            {"skill": "Django", "status": "supported", "confidence": 0.9, "evidence_ids": [], "reason": ""},
        ],
        "matched_jobs": [
            {
                "job_id": "J1", "title": "Backend Dev", "compatibility_score": 0.8,
                "semantic_score": 0.8, "structured_score": 0.8,
                "matched_skills": ["Python", "Django"], "missing_skills": [], "explanation": "x",
            }
        ],
    }
    resp = client.post("/api/rank", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == "F001"
    assert len(body["ranked_jobs"]) == 1
    assert body["ranked_jobs"][0]["fair_rank"] == 1


def test_orchestrate_requires_auth(client):
    resp = client.post("/api/orchestrate", json={
        "claimed_skills": ["Python"], "portfolio_evidence": {"evidence_items": []}
    })
    assert resp.status_code == 401


def test_orchestrate_success_with_mocked_upstreams(client, auth_headers):
    mock_verified = [VerifiedSkill(skill="Python", status="supported", confidence=0.9)]
    mock_jobs = [
        MatchedJob(
            job_id="J1", title="Backend Dev", compatibility_score=0.7,
            semantic_score=0.7, structured_score=0.7,
            matched_skills=["Python"], missing_skills=[], explanation="x",
        )
    ]

    with patch("app.main.call_skill_verification", return_value=("F001", mock_verified)), \
         patch("app.main.call_job_compatibility", return_value=mock_jobs):
        resp = client.post(
            "/api/orchestrate",
            json={
                "claimed_skills": ["Python"],
                "portfolio_evidence": {"freelancer_id": "F001", "evidence_items": []},
                "experience_years": 1.5,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == "F001"
    assert len(body["ranked_jobs"]) == 1


def test_orchestrate_upstream_failure_returns_502(client, auth_headers):
    from app.integration import UpstreamServiceError

    with patch(
        "app.main.call_skill_verification",
        side_effect=UpstreamServiceError("skill_verification_agent", "connection refused"),
    ):
        resp = client.post(
            "/api/orchestrate",
            json={
                "claimed_skills": ["Python"],
                "portfolio_evidence": {"freelancer_id": "F001", "evidence_items": []},
            },
            headers=auth_headers,
        )
    assert resp.status_code == 502


def test_full_pipeline_requires_auth(client):
    resp = client.post("/api/full-pipeline", json={
        "candidate_id": "F001", "claimed_skills": ["Python"],
    })
    assert resp.status_code == 401


def test_full_pipeline_success_with_all_mocked(client, auth_headers):
    mock_evidence = {"freelancer_id": "F001", "evidence_items": []}
    mock_verified = [VerifiedSkill(skill="Python", status="supported", confidence=0.9)]
    mock_jobs = [
        MatchedJob(
            job_id="J1", title="Backend Dev", compatibility_score=0.75,
            semantic_score=0.75, structured_score=0.75,
            matched_skills=["Python"], missing_skills=[], explanation="x",
        )
    ]

    with patch("app.main.call_portfolio_evidence", return_value=mock_evidence), \
         patch("app.main.call_skill_verification", return_value=("F001", mock_verified)), \
         patch("app.main.call_job_compatibility", return_value=mock_jobs):
        resp = client.post(
            "/api/full-pipeline",
            json={
                "candidate_id": "F001",
                "claimed_skills": ["Python"],
                "experience_years": 2.0,
                "portfolio_projects": [
                    {"project_id": "proj_001", "title": "Booking App",
                     "description": "Built with Django and REST API."}
                ],
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == "F001"
    assert len(body["ranked_jobs"]) == 1
    assert body["ranked_jobs"][0]["job_id"] == "J1"


def test_full_pipeline_portfolio_agent_failure_returns_502(client, auth_headers):
    from app.integration import UpstreamServiceError

    with patch(
        "app.main.call_portfolio_evidence",
        side_effect=UpstreamServiceError("portfolio_evidence_agent", "connection refused"),
    ):
        resp = client.post(
            "/api/full-pipeline",
            json={"candidate_id": "F001", "claimed_skills": ["Python"]},
            headers=auth_headers,
        )
    assert resp.status_code == 502
    assert resp.json()["detail"].startswith("portfolio_evidence_agent")
