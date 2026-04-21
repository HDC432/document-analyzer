from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentInfo, DocumentUploadResponse

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a PDF and trigger text extraction + embedding. Implemented in Step 2."""
    raise NotImplementedError


@router.get("/", response_model=list[DocumentInfo])
async def list_documents(
    db: Session = Depends(get_db),
) -> list[DocumentInfo]:
    """Return all uploaded documents. Implemented in Step 2."""
    raise NotImplementedError
