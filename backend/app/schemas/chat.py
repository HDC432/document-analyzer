from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    doc_id: str


class SourceCitation(BaseModel):
    page: int
    quote: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
