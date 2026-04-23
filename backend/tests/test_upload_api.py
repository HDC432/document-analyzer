"""
Integration tests for POST /api/v1/documents/upload and GET /api/v1/documents/.

Requires the `client` fixture (in-memory SQLite) and `sample_pdf` fixture
(skipped if tencent_2025.pdf is absent) from conftest.py.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import Document

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
    body = response.json()

    doc = body["document"]
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
