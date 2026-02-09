import os
import tempfile

# Create a temp directory for test database BEFORE any app imports
_tmpdir = tempfile.mkdtemp()
_tmp_db = os.path.join(_tmpdir, "test.db")
os.environ["SENTRY_DSN"] = ""  # Disable Sentry in tests

# We need to set this before core.db is imported
# But core.db reads DB_PATH at module level, so we patch after import
import core.db as db_module  # noqa: E402

db_module.DB_PATH = _tmp_db

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    db_module.DB_PATH = _tmp_db
    # Remove old DB and reinitialize
    if os.path.exists(_tmp_db):
        os.unlink(_tmp_db)
    db_module.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)
