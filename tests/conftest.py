"""
CampusAssist: Shared Pytest Fixtures.
Provides isolated in-memory seeded database instances, test clients, and contexts for test suites.
"""

import os
import tempfile
import pytest

from app import create_app
from app.models.db import init_db
from config import TestingConfig
from seed_db import seed_database


@pytest.fixture
def clean_seeded_db():
    """Initializes and seeds an in-memory SQLite database for isolated test execution."""
    conn = init_db(":memory:")
    seed_database(conn=conn, admin_password=TestingConfig.DEFAULT_ADMIN_PASSWORD)
    yield conn
    conn.close()


@pytest.fixture
def test_client():
    """Create a Flask test client with an isolated seeded test database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    seed_database(db_path=path, admin_password=TestingConfig.DEFAULT_ADMIN_PASSWORD)

    class AppTestConfig(TestingConfig):
        DB_PATH = path
        SECRET_KEY = "test-secret-key"

    app = create_app(AppTestConfig)
    with app.test_client() as client:
        yield client

    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass
