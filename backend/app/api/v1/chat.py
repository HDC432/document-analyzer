from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Answer a question grounded in the specified document. Implemented in Step 5."""
    raise NotImplementedError
