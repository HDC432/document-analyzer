"""
Retrieval service: embed query → Chroma top-k → distance filter → rerank hook.

Pipeline:
  1. embed_query()  — convert query string to a vector
  2. chroma.query() — fetch top_k candidates for this document
  3. to dataclass   — convert raw dicts to RetrievedChunk
  4. threshold      — drop chunks where distance > distance_threshold (hard filter)
  5. _rerank()      — soft re-ordering hook (identity in v1, real reranker in v2)

Distance threshold vs. _rerank separation:
  The threshold removes clearly irrelevant candidates before _rerank sees them.
  This means a v2 reranker only evaluates non-trivially-irrelevant chunks.

Empty-list contract:
  retrieve() returns [] when nothing clears the threshold.
  Callers (chat_service) MUST short-circuit and return the refusal message
  without calling the LLM — this is the primary anti-hallucination guard.

_rerank extension path:
  Subclass Retriever and override _rerank to plug in a cross-encoder or
  other reranker. No other code needs to change.
"""
from dataclasses import dataclass

from app.db.vector_store import ChromaStore
from app.services.embedding_service import EmbeddingService


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
        chroma_store: ChromaStore,
        embedding_service: EmbeddingService,
        top_k: int,
        distance_threshold: float,
    ) -> None:
        """
        Args:
            chroma_store:       ChromaStore instance (injected).
            embedding_service:  EmbeddingService instance (injected).
            top_k:              Max candidates fetched from Chroma before filtering.
            distance_threshold: Hard upper bound on cosine distance (default 0.45).
        """
        self.chroma_store = chroma_store
        self.embedding_service = embedding_service
        self.top_k = top_k
        self.distance_threshold = distance_threshold

    def retrieve(self, doc_id: str, query: str) -> list[RetrievedChunk]:
        """Embed query, fetch top-k from Chroma, filter by distance threshold.

        Steps:
          1. Embed query string via embedding_service.embed_query().
          2. Query ChromaStore for top_k candidates scoped to doc_id.
          3. Convert each result dict to a RetrievedChunk dataclass.
          4. Discard chunks with distance > distance_threshold.
          5. Pass filtered list through _rerank() and return.

        Returns:
          Filtered, re-ranked list of RetrievedChunk. Empty list when nothing
          clears the threshold — callers must short-circuit without calling LLM.
        """
        query_embedding = self.embedding_service.embed_query(query)
        raw = self.chroma_store.query(doc_id, query_embedding, top_k=self.top_k)

        filtered = [
            RetrievedChunk(
                text=r["text"],
                page_number=r["page_number"],
                distance=r["distance"],
                doc_id=r["doc_id"],
            )
            for r in raw
            if r["distance"] <= self.distance_threshold
        ]

        return self._rerank(filtered)

    def _rerank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """v1: identity. v2: override with a real reranker."""
        return chunks
