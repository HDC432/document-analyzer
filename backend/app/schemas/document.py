from datetime import datetime

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    id: str
    name: str
    page_count: int
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentInfo
