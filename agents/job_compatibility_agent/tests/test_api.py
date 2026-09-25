from fastapi.testclient import TestClient

from agents.job_compatibility_agent.app.main import app


client = TestClient(app)


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["agent"] == "job_compatibility_agent"


def test_match_jobs():

    payload = {
        "candidate_id": "F001",
        "experience_years": 0,
        "verified_skills": [
            {
                "skill": "Python",
                "status": "supported",
                "confidence": 0.97,
                "evidence_ids": ["E001"],
                "reason": "Supported by project evidence",
            },
            {
                "skill": "Pandas",
                "status": "supported",
                "confidence": 0.95,
                "evidence_ids": ["E001"],
                "reason": "Supported by project evidence",
            },
            {
                "skill": "SQL",
                "status": "supported",
                "confidence": 0.90,
                "evidence_ids": ["E002"],
                "reason": "Supported by project evidence",
            },
        ],
    }

    response = client.post(
        "/match-jobs",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["candidate_id"] == "F001"
    assert "matched_jobs" in data
    assert len(data["matched_jobs"]) > 0

    first_job = data["matched_jobs"][0]

    assert "job_id" in first_job
    assert "compatibility_score" in first_job
    assert "semantic_score" in first_job
    assert "structured_score" in first_job
    assert "matched_skills" in first_job
    assert "missing_skills" in first_job
    assert "explanation" in first_job