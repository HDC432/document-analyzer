"""
Retrieval service: embed query → Chroma top-k → distance filter → (rerank hook).

Implemented in Step 4. Stub only.

_rerank is an identity function in v1. To add a reranker in v2, subclass
Retriever and override _rerank — no other code needs to change.
"""
from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    text: str
    page_number: int
    distance: float  # cosine distance from Chroma (lower = more similar)
    doc_id: str


class Retriever:
    """Retrieve relevant chunks for a query within a single document."""

    def __init__(
        self,
        chroma_store,
        embedding_service,
        top_k: int,
        distance_threshold: float,
    ) -> None:
        """
        Args:
            chroma_store:       ChromaStore instance (injected).
            embedding_service:  EmbeddingService instance (injected).
            top_k:              Max chunks to return; sourced from settings.top_k.
            distance_threshold: Cutoff; sourced from settings.distance_threshold.
        """
        raise NotImplementedError("Implemented in Step 4")

    def retrieve(self, doc_id: str, query: str) -> list[RetrievedChunk]:
        """
        Embed query, fetch top-k from Chroma, filter by distance threshold.

        Returns an empty list when no chunk clears the threshold — the caller
        (chat_service) must short-circuit and return the refusal message without
        calling the LLM.
        """
        raise NotImplementedError

    def _rerank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """v1: identity. v2: replace with a real reranker."""
        return chunks
