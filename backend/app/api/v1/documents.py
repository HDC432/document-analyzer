import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_chroma, get_db, get_embedding_service, get_pdf_processor
from app.config import settings
from app.db.models import Document
from app.db.vector_store import ChromaStore
from app.schemas.document import DocumentInfo, DocumentUploadResponse
from app.services.embedding_service import EmbeddingService
from app.services.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    processor: PDFProcessor = Depends(get_pdf_processor),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
    chroma: ChromaStore = Depends(get_chroma),
) -> DocumentUploadResponse:
    """
    Receive a PDF, validate it, persist to disk, extract and embed chunks,
    write to Chroma, then write a Document row to SQLite.

    Flow: validate → write disk → process → embed → Chroma → DB commit
    Rollback: finally block cleans Chroma and disk file on any failure.
    """
    data = await file.read()

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds 50 MB limit")

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    if data[:4] != b"%PDF":
        raise HTTPException(415, "File is not a valid PDF")

    doc_id = str(uuid4())
    saved_path: Path | None = None
    chroma_written = False
    success = False
    try:
        saved_path = settings.uploads_path / f"{doc_id}.pdf"
        saved_path.write_bytes(data)

        page_count, chunks = processor.process(str(saved_path), doc_id=doc_id)

        # Skip embed/Chroma if no chunks (blank PDF, image-only PDF).
        # Document row is still created with chunk_count=0 so user sees the upload.
        if chunks:
            texts = [c.text for c in chunks]
            embeddings = embedding_svc.embed_texts(texts)

            # Flag before add so partial Chroma write is cleaned up on failure.
            chroma_written = True
            chroma.add(chunks, embeddings)

        logger.info(
            "Indexed doc %s: %d chunks across %d pages",
            doc_id, len(chunks), page_count,
        )

        doc = Document(
            id=doc_id,
            name=filename,
            path=str(saved_path),
            page_count=page_count,
            chunk_count=len(chunks),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        success = True
        return DocumentUploadResponse(document=DocumentInfo.model_validate(doc))

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload failed for doc %s", doc_id)
        raise HTTPException(500, "Upload processing failed") from exc

    finally:
        if not success:
            if chroma_written:
                chroma.delete_document(doc_id)
            if saved_path and saved_path.exists():
                saved_path.unlink(missing_ok=True)


@router.get("/", response_model=list[DocumentInfo])
async def list_documents(
    db: Session = Depends(get_db),
) -> list[DocumentInfo]:
    """Return all uploaded documents, newest first."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [DocumentInfo.model_validate(d) for d in docs]
