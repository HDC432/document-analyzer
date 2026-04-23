"""
Integration tests for POST /api/v1/documents/upload and GET /api/v1/documents/.

Requires the `client` fixture (in-memory SQLite + mock EmbeddingService +
real ChromaStore in tmp_path) and `sample_pdf` fixture from conftest.py.
"""
import tempfile
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

MAX_FILE_SIZE = 50 * 1024 * 1024  # must match documents.py constant


# ---------------------------------------------------------------------------
# 1. Valid upload → 201 + DB row + complete response fields
# ---------------------------------------------------------------------------

def test_upload_pdf_creates_document(client: TestClient, sample_pdf: Path) -> None:
    """Upload a real PDF → 201, Document row in DB, all response fields present."""
    with sample_pdf.open("rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": (sample_pdf.name, f, "application/pdf")},
        )

    assert response.status_code == 201, response.text
    doc = response.json()["document"]
    assert doc["id"]
    assert doc["name"] == sample_pdf.name
    assert doc["page_count"] > 0
    assert doc["chunk_count"] > 0
    assert doc["created_at"]


# ---------------------------------------------------------------------------
# 2. Non-PDF filename → 400
# ---------------------------------------------------------------------------

def test_upload_rejects_non_pdf_filename(client: TestClient) -> None:
    """File whose name doesn't end in .pdf must be rejected with 400."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("report.txt", b"some text content", "text/plain")},
    )
    assert response.status_code == 400, response.text


# ---------------------------------------------------------------------------
# 3. .pdf extension but wrong magic bytes → 415
# ---------------------------------------------------------------------------

def test_upload_rejects_invalid_magic_bytes(client: TestClient) -> None:
    """File with .pdf suffix but non-PDF content must be rejected with 415."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("fake.pdf", b"NOT_A_PDF_CONTENT", "application/pdf")},
    )
    assert response.status_code == 415, response.text


# ---------------------------------------------------------------------------
# 4. File > 50 MB → 413
# ---------------------------------------------------------------------------

def test_upload_rejects_oversized_file(client: TestClient) -> None:
    """File exceeding 50 MB must be rejected with 413 before any processing."""
    oversized = b"x" * (MAX_FILE_SIZE + 1)
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413, response.text


# ---------------------------------------------------------------------------
# 5. GET / returns uploaded document, newest first
# ---------------------------------------------------------------------------

def test_list_documents_returns_uploaded(client: TestClient, sample_pdf: Path) -> None:
    """After upload, GET /api/v1/documents/ must include the new document."""
    with sample_pdf.open("rb") as f:
        upload_resp = client.post(
            "/api/v1/documents/upload",
            files={"file": (sample_pdf.name, f, "application/pdf")},
        )
    assert upload_resp.status_code == 201
    uploaded_id = upload_resp.json()["document"]["id"]

    list_resp = client.get("/api/v1/documents/")
    assert list_resp.status_code == 200
    ids = [d["id"] for d in list_resp.json()]
    assert uploaded_id in ids


# ---------------------------------------------------------------------------
# 6. Upload writes correct chunk count to Chroma
# ---------------------------------------------------------------------------

def test_upload_writes_to_chroma(client: TestClient, sample_pdf: Path) -> None:
    """chunk_count in response must match the number of vectors in Chroma."""
    with sample_pdf.open("rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": (sample_pdf.name, f, "application/pdf")},
        )
    assert response.status_code == 201
    doc = response.json()["document"]
    assert client.test_chroma.count(doc["id"]) == doc["chunk_count"]


# ---------------------------------------------------------------------------
# 7. Blank PDF (no text) → 201 + chunk_count=0 + no embedding/Chroma calls
# ---------------------------------------------------------------------------

def test_upload_empty_pdf_succeeds_with_zero_chunks(client: TestClient) -> None:
    """PDF with pages but no text → 201, chunk_count=0, no embedding or Chroma writes."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp = Path(f.name)
    try:
        pdf_doc = fitz.open()
        pdf_doc.new_page()
        pdf_doc.save(str(tmp))
        pdf_doc.close()

        with tmp.open("rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("blank.pdf", f, "application/pdf")},
            )

        assert response.status_code == 201, response.text
        data = response.json()["document"]
        assert data["page_count"] == 1
        assert data["chunk_count"] == 0

        client.mock_embedding_svc.embed_texts.assert_not_called()
        assert client.test_chroma.total_count() == 0
    finally:
        tmp.unlink(missing_ok=True)
