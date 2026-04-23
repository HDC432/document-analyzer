"""
Unit tests for EmbeddingService.

OpenAI client is mocked — no real API calls are made.
"""
from unittest.mock import MagicMock, call

import pytest

from app.services.embedding_service import BATCH_SIZE, EmbeddingService

DIM = 1536


def _make_mock_client(dim: int = DIM) -> MagicMock:
    """Mock OpenAI client whose embeddings.create returns one vector per input."""
    client = MagicMock()

    def _create(input, model):
        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.1] * dim) for _ in input]
        return resp

    client.embeddings.create.side_effect = _create
    return client


@pytest.fixture
def service() -> EmbeddingService:
    return EmbeddingService(
        openai_client=_make_mock_client(),
        model="text-embedding-3-small",
    )


# ---------------------------------------------------------------------------
# 1. One vector returned per input text
# ---------------------------------------------------------------------------

def test_embed_texts_returns_one_vector_per_input(service: EmbeddingService) -> None:
    texts = ["text one", "text two", "text three", "text four", "text five"]
    result = service.embed_texts(texts)

    assert len(result) == 5
    for vec in result:
        assert isinstance(vec, list)
        assert len(vec) == DIM
        assert all(isinstance(v, float) for v in vec)


# ---------------------------------------------------------------------------
# 2. Large input triggers multiple batches (100 + 100 + 50 = 250)
# ---------------------------------------------------------------------------

def test_embed_texts_batches_correctly() -> None:
    mock_client = _make_mock_client()
    svc = EmbeddingService(openai_client=mock_client, model="text-embedding-3-small")

    texts = [f"chunk {i}" for i in range(250)]
    result = svc.embed_texts(texts)

    assert len(result) == 250

    create = mock_client.embeddings.create
    assert create.call_count == 3

    batch_sizes = [len(c.kwargs["input"]) for c in create.call_args_list]
    assert batch_sizes == [BATCH_SIZE, BATCH_SIZE, 50]


# ---------------------------------------------------------------------------
# 3. embed_query returns a single vector, not a list-of-lists
# ---------------------------------------------------------------------------

def test_embed_query_returns_single_vector(service: EmbeddingService) -> None:
    result = service.embed_query("腾讯2025总收入")

    assert isinstance(result, list)
    assert len(result) == DIM
    assert isinstance(result[0], float)


# ---------------------------------------------------------------------------
# 4. Empty input returns [] without calling the API
# ---------------------------------------------------------------------------

def test_embed_texts_empty_input_returns_empty() -> None:
    mock_client = _make_mock_client()
    svc = EmbeddingService(openai_client=mock_client, model="text-embedding-3-small")

    result = svc.embed_texts([])

    assert result == []
    mock_client.embeddings.create.assert_not_called()
