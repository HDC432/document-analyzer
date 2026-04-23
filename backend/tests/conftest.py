import os
from pathlib import Path
from unittest.mock import MagicMock

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
from app.api.deps import get_chroma, get_db, get_embedding_service
from app.config import settings
from app.db.database import Base
from app.db.vector_store import ChromaStore
from app.services.embedding_service import EmbeddingService

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
    # Isolated writable uploads directory per test.
    tmp_uploads = tmp_path / "uploads"
    tmp_uploads.mkdir()
    monkeypatch.setattr(settings, "uploads_path", tmp_uploads)

    # In-memory SQLite with StaticPool so all connections share one DB.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    # Mock EmbeddingService — returns fixed 1536-dim vectors, no OpenAI calls.
    mock_embedding_svc = MagicMock(spec=EmbeddingService)
    mock_embedding_svc.embed_texts.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
    mock_embedding_svc.embed_query.side_effect = lambda text: [0.1] * 1536

    # Real ChromaStore in isolated tmp_path — verifies actual Chroma writes.
    test_chroma = ChromaStore(path=tmp_path / "chroma")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_svc
    app.dependency_overrides[get_chroma] = lambda: test_chroma

    with TestClient(app) as c:
        c.test_chroma = test_chroma
        c.mock_embedding_svc = mock_embedding_svc
        yield c

    app.dependency_overrides.clear()
