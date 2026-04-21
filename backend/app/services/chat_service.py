"""
RAG answer generation service.

Implemented in Step 5. Stub only.

翻车点 3 规避: answer() 调用 retriever 后,若返回空列表则直接
短路返回 REFUSAL_MESSAGE,不调用 LLM。短路逻辑在 ChatService
层,不泄漏到路由。
"""
from app.schemas.chat import ChatResponse
from app.services.retrieval_service import Retriever

REFUSAL_MESSAGE = (
    "未在当前文档中找到相关信息。\n"
    "No relevant information was found in the current document."
)


class ChatService:
    """Orchestrate retrieval + LLM to produce grounded answers with citations."""

    def __init__(self, retriever: Retriever, openai_client, model: str) -> None:
        """
        Args:
            retriever:     Retriever instance (injected).
            openai_client: openai.OpenAI instance (injected).
            model:         Chat model name from settings.chat_model.
        """
        raise NotImplementedError("Implemented in Step 5")

    def answer(self, question: str, doc_id: str) -> ChatResponse:
        """
        Retrieve chunks, then call LLM with RAG prompt.

        Short-circuits with REFUSAL_MESSAGE (no LLM call) when retriever
        returns an empty list (all chunks below distance threshold).

        Args:
            question: User question string.
            doc_id:   Document UUID to scope retrieval.

        Returns:
            ChatResponse with answer text and source citations.
        """
        raise NotImplementedError
