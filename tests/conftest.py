"""Test setup: isolated SQLite database and deterministic environment, set before the app imports config."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_tmp = Path(tempfile.mkdtemp(prefix="hcx_tests_"))
os.environ["DATABASE_PATH"] = str(_tmp / "test.db")
os.environ["ADMIN_EMAIL"] = "admin@test.example"
os.environ["ADMIN_PASSWORD"] = "Admin@Test123"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["DEMO_PASSWORD"] = "Demo@12345"

import pytest  # noqa: E402

import config  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Fresh database per test."""
    from database import init_db

    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path / "fresh.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    init_db()
    return tmp_path
