def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_valid_request_returns_200(client):
    payload = {
        "candidate_id": "F001",
        "claimed_skills": ["Python", "Django", "Machine Learning", "React"],
        "evidence": [
            {
                "evidence_id": "E001",
                "project": "Online Booking System",
                "description": "Built a web-based booking platform using Django and REST APIs.",
                "extracted_skills": ["Python", "Django", "REST API", "Web Development"],
            }
        ],
    }
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == "F001"
    assert len(body["verified_skills"]) == 4


def test_missing_required_field_returns_422(client):
    # missing claimed_skills entirely
    payload = {"candidate_id": "F002", "evidence": []}
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 422


def test_empty_claimed_skills_returns_422(client):
    payload = {"candidate_id": "F003", "claimed_skills": [], "evidence": []}
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 422


def test_malformed_json_returns_422(client):
    resp = client.post(
        "/api/verify-skills",
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_invalid_data_type_returns_422(client):
    # claimed_skills should be a list of strings, not a string
    payload = {"candidate_id": "F004", "claimed_skills": "Python", "evidence": []}
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 422


def test_empty_evidence_list_still_processes(client):
    payload = {"candidate_id": "F011", "claimed_skills": ["Python"], "evidence": []}
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 200
    assert resp.json()["verified_skills"][0]["status"] == "unsupported"


def test_duplicate_skills_deduplicated(client):
    payload = {
        "candidate_id": "F012",
        "claimed_skills": ["Python", "python", "PYTHON"],
        "evidence": [
            {
                "evidence_id": "E012",
                "project": "Blog",
                "description": "Built with Django.",
                "extracted_skills": ["Python", "Django"],
            }
        ],
    }
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 200
    assert len(resp.json()["verified_skills"]) == 1


def test_unsupported_skill_flagged(client):
    payload = {
        "candidate_id": "F002",
        "claimed_skills": ["React"],
        "evidence": [
            {
                "evidence_id": "E002",
                "project": "Portfolio Site",
                "description": "Static HTML/CSS website.",
                "extracted_skills": ["HTML", "CSS"],
            }
        ],
    }
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 200
    assert resp.json()["verified_skills"][0]["status"] == "unsupported"


def test_overlong_candidate_id_returns_422(client):
    payload = {
        "candidate_id": "F" * 200,
        "claimed_skills": ["Python"],
        "evidence": [],
    }
    resp = client.post("/api/verify-skills", json=payload)
    assert resp.status_code == 422
