import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import settings
from sqlalchemy import create_engine

# HYPOTHESIS_PROFILE=ci for the 10,000-plan run in acceptance criterion 6.
settings.register_profile("ci", max_examples=10_000, deadline=None)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

# Point the app at a throwaway SQLite file and an unreachable Qdrant before any app module is imported.
_DB_PATH = Path(tempfile.mkdtemp(prefix="sentinel-tests-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"
os.environ["QDRANT_URL"] = "http://127.0.0.1:9"
os.environ["APP_ENV"] = "test"

from app.database.models import Base  # noqa: E402

sync_engine = create_engine(f"sqlite:///{_DB_PATH.as_posix()}")
Base.metadata.create_all(sync_engine)


@pytest.fixture
def db():
    """Empties every table before and after a test; yields a sync engine for assertions."""
    def clear():
        with sync_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())

    clear()
    yield sync_engine
    clear()
