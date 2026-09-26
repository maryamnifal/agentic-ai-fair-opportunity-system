def _rank_payload():
    return {
        "candidate_id": "F001",
        "claimed_skills": ["Python"],
        "verified_skills": [],
        "matched_jobs": [],
    }


def test_requests_within_limit_succeed(client, auth_headers):
    for _ in range(5):
        resp = client.post("/api/rank", json=_rank_payload(), headers=auth_headers)
        assert resp.status_code == 200


def test_exceeding_rate_limit_returns_429(client, auth_headers):
    from app.rate_limit import MAX_REQUESTS

    last_status = None
    for _ in range(MAX_REQUESTS + 2):
        resp = client.post("/api/rank", json=_rank_payload(), headers=auth_headers)
        last_status = resp.status_code

    assert last_status == 429
