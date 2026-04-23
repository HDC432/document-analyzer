"""
Unit tests for Retriever.

ChromaStore and EmbeddingService are mocked — Retriever is pure composition
logic with no I/O of its own, so unit tests are sufficient here.
"""
from unittest.mock import MagicMock

import pytest

from app.services.retrieval_service import RetrievedChunk, Retriever

THRESHOLD = 0.45
TOP_K = 5


@pytest.fixture
def mock_chroma() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_embedding() -> MagicMock:
    m = MagicMock()
    m.embed_query.return_value = [0.1] * 1536
    return m


@pytest.fixture
def retriever(mock_chroma: MagicMock, mock_embedding: MagicMock) -> Retriever:
    return Retriever(
        chroma_store=mock_chroma,
        embedding_service=mock_embedding,
        top_k=TOP_K,
        distance_threshold=THRESHOLD,
    )


def _make_raw_chunk(distance: float, **overrides) -> dict:
    """Build a dict matching ChromaStore.query's return format."""
    base = {
        "text": "sample text",
        "page_number": 1,
        "chunk_index": 0,
        "doc_id": "test-doc",
        "distance": distance,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. All chunks under threshold → all returned with correct fields
# ---------------------------------------------------------------------------

def test_retrieve_returns_chunks_under_threshold(
    retriever: Retriever, mock_chroma: MagicMock, mock_embedding: MagicMock
) -> None:
    raw = [
        _make_raw_chunk(0.1, text="chunk A", page_number=1, chunk_index=0),
        _make_raw_chunk(0.3, text="chunk B", page_number=2, chunk_index=1),
        _make_raw_chunk(0.4, text="chunk C", page_number=3, chunk_index=2),
    ]
    mock_chroma.query.return_value = raw

    results = retriever.retrieve("test-doc", "some query")

    assert len(results) == 3
    assert all(isinstance(c, RetrievedChunk) for c in results)

    assert results[0].text == "chunk A"
    assert results[0].page_number == 1
    assert results[0].distance == 0.1
    assert results[0].doc_id == "test-doc"

    mock_embedding.embed_query.assert_called_once_with("some query")
    mock_chroma.query.assert_called_once_with(
        "test-doc", [0.1] * 1536, top_k=TOP_K
    )


# ---------------------------------------------------------------------------
# 2. Mixed distances → only chunks at or below threshold are kept, order preserved
# ---------------------------------------------------------------------------

def test_retrieve_filters_chunks_above_threshold(
    retriever: Retriever, mock_chroma: MagicMock
) -> None:
    distances = [0.1, 0.3, 0.5, 0.6, 0.2]
    mock_chroma.query.return_value = [
        _make_raw_chunk(d, chunk_index=i) for i, d in enumerate(distances)
    ]

    results = retriever.retrieve("test-doc", "query")

    assert len(results) == 3
    returned_distances = [c.distance for c in results]
    # order matches chroma's original order (rerank is identity)
    assert returned_distances == [0.1, 0.3, 0.2]


# ---------------------------------------------------------------------------
# 3. All chunks above threshold → [] (short-circuit contract for chat_service)
# ---------------------------------------------------------------------------

def test_retrieve_returns_empty_when_all_above_threshold(
    retriever: Retriever, mock_chroma: MagicMock
) -> None:
    mock_chroma.query.return_value = [
        _make_raw_chunk(0.5),
        _make_raw_chunk(0.7),
        _make_raw_chunk(0.9),
    ]

    results = retriever.retrieve("test-doc", "query")

    assert results == []


# ---------------------------------------------------------------------------
# 4. Chroma returns empty list → [] without raising
# ---------------------------------------------------------------------------

def test_retrieve_returns_empty_when_chroma_returns_empty(
    retriever: Retriever, mock_chroma: MagicMock
) -> None:
    mock_chroma.query.return_value = []

    results = retriever.retrieve("nonexistent-doc", "query")

    assert results == []


# ---------------------------------------------------------------------------
# 5. _rerank receives post-filter chunks (not pre-filter) — D2 order verified
# ---------------------------------------------------------------------------

def test_retrieve_calls_rerank_after_filter(
    mock_chroma: MagicMock, mock_embedding: MagicMock
) -> None:
    rerank_input: list[RetrievedChunk] = []

    class TrackingRetriever(Retriever):
        def _rerank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
            rerank_input.extend(chunks)
            return chunks

    retriever = TrackingRetriever(
        chroma_store=mock_chroma,
        embedding_service=mock_embedding,
        top_k=TOP_K,
        distance_threshold=THRESHOLD,
    )

    # 5 chunks returned, only 3 clear the threshold
    mock_chroma.query.return_value = [
        _make_raw_chunk(0.1), _make_raw_chunk(0.2), _make_raw_chunk(0.5),
        _make_raw_chunk(0.6), _make_raw_chunk(0.3),
    ]

    retriever.retrieve("test-doc", "query")

    assert len(rerank_input) == 3
    assert all(c.distance <= THRESHOLD for c in rerank_input)
