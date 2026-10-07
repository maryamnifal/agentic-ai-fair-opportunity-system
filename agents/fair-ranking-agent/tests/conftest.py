import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402
from app.users_store import reset_store_for_tests  # noqa: E402
from app.rate_limit import reset_rate_limits_for_tests  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_state():
    reset_store_for_tests()
    reset_rate_limits_for_tests()
    yield
    reset_store_for_tests()
    reset_rate_limits_for_tests()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    client.post("/auth/register", json={"username": "tester", "password": "supersecret1"})
    resp = client.post(
        "/auth/login",
        data={"username": "tester", "password": "supersecret1"},
    )
    return resp.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
