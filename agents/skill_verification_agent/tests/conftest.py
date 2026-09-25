import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Allow `import app...` when running pytest from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
