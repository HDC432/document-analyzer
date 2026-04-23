"""
Integration tests for ChromaStore using a real PersistentClient in tmp_path.

No mocks — Chroma local operations are millisecond-level, so real client
is fast and gives higher confidence than mocking chromadb internals.
"""
from pathlib import Path

import pytest

from app.db.vector_store import ChromaStore
from app.services.pdf_processor import Chunk

TOTAL_DIM = 1536


@pytest.fixture
def store(tmp_path: Path) -> ChromaStore:
    """Fresh ChromaStore in an isolated tmp directory."""
    return ChromaStore(path=tmp_path / "chroma")


def _make_chunk(doc_id: str, idx: int, page: int = 1, text: str = "") -> Chunk:
    return Chunk(
        text=text or f"text-{idx}",
        page_number=page,
        chunk_index=idx,
        doc_id=doc_id,
    )


def _one_hot(dim_index: int) -> list[float]:
    """One-hot embedding with 1.0 at dim_index, 0.0 elsewhere."""
    e = [0.0] * TOTAL_DIM
    e[dim_index] = 1.0
    return e


# ---------------------------------------------------------------------------
# 1. add + count for a single document
# ---------------------------------------------------------------------------

def test_add_and_count_for_single_doc(store: ChromaStore) -> None:
    chunks = [_make_chunk("doc-a", i) for i in range(3)]
    embeddings = [_one_hot(i) for i in range(3)]

    store.add(chunks, embeddings)

    assert store.count("doc-a") == 3
    assert store.total_count() == 3


# ---------------------------------------------------------------------------
# 2. count isolates per-document
# ---------------------------------------------------------------------------

def test_count_isolates_docs(store: ChromaStore) -> None:
    store.add([_make_chunk("doc-a", i) for i in range(2)], [_one_hot(i) for i in range(2)])
    store.add([_make_chunk("doc-b", i) for i in range(3)], [_one_hot(i) for i in range(3)])

    assert store.count("doc-a") == 2
    assert store.count("doc-b") == 3
    assert store.total_count() == 5


# ---------------------------------------------------------------------------
# 3. query returns most similar chunk first
# ---------------------------------------------------------------------------

def test_query_returns_most_similar_first(store: ChromaStore) -> None:
    chunks = [
        _make_chunk("doc-a", 0, text="chunk zero"),
        _make_chunk("doc-a", 1, text="chunk one"),
        _make_chunk("doc-a", 2, text="chunk two"),
    ]
    embeddings = [_one_hot(0), _one_hot(1), _one_hot(2)]
    store.add(chunks, embeddings)

    results = store.query("doc-a", _one_hot(0), top_k=3)

    assert len(results) == 3
    assert results[0]["chunk_index"] == 0
    assert results[0]["text"] == "chunk zero"
    assert results[0]["distance"] < results[1]["distance"]

    first = results[0]
    assert "text" in first
    assert "page_number" in first
    assert "chunk_index" in first
    assert "doc_id" in first
    assert "distance" in first


# ---------------------------------------------------------------------------
# 4. query respects doc_id filter
# ---------------------------------------------------------------------------

def test_query_respects_doc_id_filter(store: ChromaStore) -> None:
    store.add([_make_chunk("doc-a", 0, text="alpha")], [_one_hot(0)])
    store.add([_make_chunk("doc-b", 0, text="beta")], [_one_hot(0)])

    results = store.query("doc-a", _one_hot(0), top_k=5)

    assert len(results) == 1
    assert results[0]["doc_id"] == "doc-a"
    assert results[0]["text"] == "alpha"


# ---------------------------------------------------------------------------
# 5. delete_document removes all chunks for that doc
# ---------------------------------------------------------------------------

def test_delete_document_removes_all_chunks(store: ChromaStore) -> None:
    chunks = [_make_chunk("doc-a", i) for i in range(3)]
    store.add(chunks, [_one_hot(i) for i in range(3)])

    store.delete_document("doc-a")

    assert store.count("doc-a") == 0
    assert store.total_count() == 0


# ---------------------------------------------------------------------------
# 6. persistence across re-init (翻车点 2 规避验证)
# ---------------------------------------------------------------------------

def test_persistence_across_reinit(tmp_path: Path) -> None:
    chroma_path = tmp_path / "chroma"

    store1 = ChromaStore(path=chroma_path)
    store1.add(
        [_make_chunk("doc-persist", i) for i in range(3)],
        [_one_hot(i) for i in range(3)],
    )
    del store1

    store2 = ChromaStore(path=chroma_path)
    assert store2.count("doc-persist") == 3
    results = store2.query("doc-persist", _one_hot(0), top_k=1)
    assert results[0]["chunk_index"] == 0
