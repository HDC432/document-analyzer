import os
from pathlib import Path

# Must precede all app imports — Settings() is a module-level singleton
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("SQLITE_PATH", "/tmp/doc_analyzer_test/app.db")
os.environ.setdefault("CHROMA_PATH", "/tmp/doc_analyzer_test/chroma")
os.environ.setdefault("UPLOADS_PATH", "/tmp/doc_analyzer_test/uploads")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.config import settings
from app.db.database import Base

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "tencent_2025.pdf"


@pytest.fixture
def sample_pdf() -> Path:
    """
    Return path to the sample Tencent annual report PDF.
    Skip the test if the file is not present.
    """
    if not SAMPLE_PDF.exists():
        pytest.skip(f"Sample PDF not found at {SAMPLE_PDF}")
    return SAMPLE_PDF


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Give each test an isolated, writable uploads directory.
    tmp_uploads = tmp_path / "uploads"
    tmp_uploads.mkdir()
    monkeypatch.setattr(settings, "uploads_path", tmp_uploads)

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share single in-memory DB across connections
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
