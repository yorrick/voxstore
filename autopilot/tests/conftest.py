import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set required env vars BEFORE importing the app module
os.environ["SENTRY_WEBHOOK_SECRET"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from autopilot.webhook_server import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
