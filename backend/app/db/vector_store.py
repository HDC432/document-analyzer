"""
Chroma vector store wrapper.

Responsibilities:
- Persist chunk embeddings and metadata via chromadb.PersistentClient.
- Provide add / query / count / delete operations used by the upload and
  retrieval pipeline.

Design notes:
- No dependency on OpenAI or EmbeddingService — embeddings are passed in
  as plain float lists, keeping concerns separated.
- Persistence path is injected through the constructor; no global state.
- Collection uses cosine distance ("hnsw:space": "cosine") which matches
  the unit-normalized output of OpenAI text-embedding-3-small.
- 翻车点 2 规避: PersistentClient writes to the injected path; callers
  must assert write permission before constructing this object (done in
  app lifespan).
"""
from pathlib import Path

import chromadb

from app.services.pdf_processor import Chunk

COLLECTION_NAME = "documents"


class ChromaStore:
    """Wraps chromadb.PersistentClient for document chunk storage and retrieval."""

    def __init__(self, path: Path) -> None:
        self._client = chromadb.PersistentClient(path=str(path))
        self._col = self._client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Store chunk embeddings and metadata.

        Args:
            chunks:     Chunk objects from PDFProcessor (text + metadata).
            embeddings: Parallel list of embedding vectors from EmbeddingService.
        """
        self._col.add(
            ids=[f"{c.doc_id}:{c.chunk_index}" for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ],
        )

    def query(
        self, doc_id: str, embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """Return top-k chunks for doc_id ranked by cosine distance (ascending).

        Args:
            doc_id:    Restrict results to this document.
            embedding: Query vector from EmbeddingService.embed_query().
            top_k:     Maximum number of results to return.

        Returns:
            List of dicts with keys: text, page_number, chunk_index, doc_id, distance.
        """
        results = self._col.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where={"doc_id": doc_id},
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]
        return [
            {
                "text": text,
                "page_number": meta["page_number"],
                "chunk_index": meta["chunk_index"],
                "doc_id": meta["doc_id"],
                "distance": dist,
            }
            for text, meta, dist in zip(docs, metas, dists)
        ]

    def count(self, doc_id: str) -> int:
        """Return number of chunks stored for a specific document.

        Uses get() with include=[] (ids only) because collection.count()
        does not accept a where filter.
        """
        result = self._col.get(where={"doc_id": doc_id}, include=[])
        return len(result["ids"])

    def total_count(self) -> int:
        """Return total number of chunks across all documents."""
        return self._col.count()

    def delete_document(self, doc_id: str) -> None:
        """Delete all chunks for a document. Used for upload rollback."""
        self._col.delete(where={"doc_id": doc_id})
