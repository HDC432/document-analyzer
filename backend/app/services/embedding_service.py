"""
OpenAI embedding service.

Implemented in Step 3. Stub only.
openai_client is injected (not hardcoded) to allow mocking in tests.
"""


class EmbeddingService:
    """Batch-encode texts using OpenAI text-embedding-3-small."""

    def __init__(self, openai_client, model: str) -> None:
        """
        Args:
            openai_client: openai.OpenAI instance (injected).
            model:         Embedding model name from settings.embedding_model.
        """
        raise NotImplementedError("Implemented in Step 3")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text (batched)."""
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        """Return a single embedding vector for a query string."""
        raise NotImplementedError
