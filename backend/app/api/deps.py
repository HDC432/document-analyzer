"""
FastAPI dependency providers.

get_db is ready for use. get_chroma and get_embedding_service are stubs
filled in Steps 3 and 2 respectively — they raise NotImplementedError so
any route that Depends on them will 500 until implemented.
"""
from typing import Generator

from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.services.pdf_processor import PDFProcessor


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pdf_processor() -> PDFProcessor:
    """Factory for PDFProcessor, configured from settings."""
    return PDFProcessor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def get_chroma():
    """Yield a ChromaStore instance. Implemented in Step 3."""
    raise NotImplementedError("Implemented in Step 3")


def get_embedding_service():
    """Yield an EmbeddingService instance. Implemented in Step 2."""
    raise NotImplementedError("Implemented in Step 2")
