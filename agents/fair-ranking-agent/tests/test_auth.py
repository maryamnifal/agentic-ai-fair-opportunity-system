def test_register_new_user(client):
    resp = client.post("/auth/register", json={"username": "alice", "password": "password123"})
    assert resp.status_code == 201


def test_register_duplicate_user_rejected(client):
    client.post("/auth/register", json={"username": "bob", "password": "password123"})
    resp = client.post("/auth/register", json={"username": "bob", "password": "password123"})
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={"username": "carol", "password": "password123"})
    resp = client.post("/auth/login", json={"username": "carol", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_success_returns_token(client):
    client.post("/auth/register", json={"username": "dave", "password": "password123"})
    resp = client.post("/auth/login", json={"username": "dave", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_protected_endpoint_without_token_returns_401(client):
    resp = client.post("/api/rank", json={
        "candidate_id": "F001", "claimed_skills": ["Python"],
        "verified_skills": [], "matched_jobs": []
    })
    assert resp.status_code == 401


def test_protected_endpoint_with_invalid_token_returns_401(client):
    resp = client.post(
        "/api/rank",
        json={"candidate_id": "F001", "claimed_skills": ["Python"], "verified_skills": [], "matched_jobs": []},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token_succeeds(client, auth_headers):
    resp = client.post(
        "/api/rank",
        json={"candidate_id": "F001", "claimed_skills": ["Python"], "verified_skills": [], "matched_jobs": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
