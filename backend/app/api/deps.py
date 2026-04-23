"""
FastAPI dependency providers.

Returns configured service instances per request. See individual
factory docstrings for construction details.
"""
from typing import Generator

from fastapi import Depends
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.db.vector_store import ChromaStore
from app.services.embedding_service import EmbeddingService
from app.services.pdf_processor import PDFProcessor
from app.services.retrieval_service import Retriever


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


def get_chroma() -> ChromaStore:
    """Factory for ChromaStore, configured from settings."""
    return ChromaStore(path=settings.chroma_path)


def get_embedding_service() -> EmbeddingService:
    """Factory for EmbeddingService, configured from settings."""
    return EmbeddingService(
        openai_client=OpenAI(api_key=str(settings.openai_api_key)),
        model=settings.embedding_model,
    )


def get_retriever(
    chroma: ChromaStore = Depends(get_chroma),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
) -> Retriever:
    """Factory for Retriever. Composes ChromaStore + EmbeddingService + settings."""
    return Retriever(
        chroma_store=chroma,
        embedding_service=embedding_svc,
        top_k=settings.top_k,
        distance_threshold=settings.distance_threshold,
    )
