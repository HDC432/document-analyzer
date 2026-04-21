"""
FastAPI dependency providers.

get_db is ready for use. get_chroma and get_embedding_service are stubs
filled in Steps 3 and 2 respectively — they raise NotImplementedError so
any route that Depends on them will 500 until implemented.
"""
from typing import Generator

from sqlalchemy.orm import Session

from app.db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chroma():
    """Yield a ChromaStore instance. Implemented in Step 3."""
    raise NotImplementedError("Implemented in Step 3")


def get_embedding_service():
    """Yield an EmbeddingService instance. Implemented in Step 2."""
    raise NotImplementedError("Implemented in Step 2")
