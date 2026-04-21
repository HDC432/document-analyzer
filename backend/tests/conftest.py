import os

# Must precede all app imports — Settings() is a module-level singleton
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("SQLITE_PATH", "/tmp/doc_analyzer_test/app.db")
os.environ.setdefault("CHROMA_PATH", "/tmp/doc_analyzer_test/chroma")
os.environ.setdefault("UPLOADS_PATH", "/tmp/doc_analyzer_test/uploads")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.deps import get_db
from app.db.database import Base


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
