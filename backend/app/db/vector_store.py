"""
Chroma vector store wrapper.

Stub only — implemented in Step 3.
翻车点 2 规避: PersistentClient + 写权限断言 + lifespan 打印 count。
"""
from pathlib import Path


class ChromaStore:
    """Wraps chromadb.PersistentClient for document chunk storage and retrieval."""

    def __init__(self, path: Path) -> None:
        raise NotImplementedError("Implemented in Step 3")

    def add(self, doc_id: str, chunks: list[dict]) -> None:
        """Store chunk embeddings and metadata for a document."""
        raise NotImplementedError

    def query(self, doc_id: str, embedding: list[float], top_k: int = 5) -> list[dict]:
        """Return top-k chunks for doc_id closest to the given embedding."""
        raise NotImplementedError

    def count(self, doc_id: str) -> int:
        """Return number of chunks stored for a document."""
        raise NotImplementedError
