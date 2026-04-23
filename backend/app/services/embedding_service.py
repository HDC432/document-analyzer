"""
OpenAI embedding service.

openai_client is injected (not hardcoded) to allow mocking in tests.
Texts are sent in batches of BATCH_SIZE to stay well within OpenAI's
per-request token limits (~30k tokens per batch at 300 tokens/chunk).
"""

BATCH_SIZE = 100


class EmbeddingService:
    """Batch-encode texts using an injected OpenAI client."""

    def __init__(self, openai_client, model: str) -> None:
        """
        Args:
            openai_client: openai.OpenAI instance (injected for testability).
            model:         Embedding model name, e.g. "text-embedding-3-small".
        """
        self._client = openai_client
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        Splits texts into batches of BATCH_SIZE and concatenates results.
        Raises on API error — callers are responsible for cleanup.
        """
        results: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            resp = self._client.embeddings.create(input=batch, model=self._model)
            results.extend(item.embedding for item in resp.data)
        return results

    def embed_query(self, text: str) -> list[float]:
        """Return a single embedding vector for a query string."""
        return self.embed_texts([text])[0]
