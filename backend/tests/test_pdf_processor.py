"""
Unit tests for PDFProcessor.

All tests except test_empty_pdf_returns_zero_pages require
backend/tests/fixtures/tencent_2025.pdf.
Missing file → pytest.skip (see conftest.py sample_pdf fixture).
"""
import tempfile
from pathlib import Path

import fitz
import pytest

from app.services.pdf_processor import Chunk, PDFProcessor


@pytest.fixture
def processor() -> PDFProcessor:
    return PDFProcessor(chunk_size=500, chunk_overlap=80)


# ---------------------------------------------------------------------------
# a) 中文不乱码
# ---------------------------------------------------------------------------

def test_no_garbled_chinese(processor: PDFProcessor, sample_pdf: Path) -> None:
    """Extracted text must contain expected Chinese and no replacement chars."""
    page_count, chunks = processor.process(str(sample_pdf), doc_id="test-doc")
    assert chunks, "Expected at least one chunk"

    full_text = " ".join(c.text for c in chunks[:30])  # first 30 chunks ≈ first 3 pages

    assert any(kw in full_text for kw in ("腾讯", "騰訊", "二零二五", "2025")), (
        "Expected Chinese keywords not found in first pages"
    )
    assert "�" not in full_text, (
        "Replacement character \\ufffd found — possible encoding issue"
    )


# ---------------------------------------------------------------------------
# b) page_number 1-indexed 且不超过 page_count
# ---------------------------------------------------------------------------

def test_page_numbers_one_indexed(processor: PDFProcessor, sample_pdf: Path) -> None:
    """All chunk page_numbers must be >= 1 and <= page_count."""
    page_count, chunks = processor.process(str(sample_pdf), doc_id="test-doc")
    assert chunks

    page_numbers = [c.page_number for c in chunks]
    assert min(page_numbers) >= 1, "page_number must be 1-indexed (no 0)"
    assert max(page_numbers) <= page_count, (
        f"page_number {max(page_numbers)} exceeds page_count {page_count}"
    )


# ---------------------------------------------------------------------------
# c) chunk_index 全局连续无间隙
# ---------------------------------------------------------------------------

def test_chunk_index_globally_continuous(processor: PDFProcessor, sample_pdf: Path) -> None:
    """chunk_index must be 0-based and continuous across all pages."""
    _, chunks = processor.process(str(sample_pdf), doc_id="test-doc")
    assert chunks

    indices = [c.chunk_index for c in chunks]
    assert indices[0] == 0, "First chunk_index must be 0"
    assert indices == list(range(len(chunks))), (
        "chunk_index values are not a continuous sequence [0, 1, 2, ...]"
    )


# ---------------------------------------------------------------------------
# d) chunk 长度在合理区间（三层断言）
# ---------------------------------------------------------------------------

def test_chunk_length_within_bounds(processor: PDFProcessor, sample_pdf: Path) -> None:
    """
    Three-layer length assertion:
      - Hard lower bound:  all chunks >= 10 chars (filter threshold)
      - Hard upper bound:  all chunks <= chunk_size + 50 (paragraph slack)
      - Soft threshold:    >= 85% of MIDDLE chunks in [chunk_size // 2, chunk_size].
                           The lower bound is chunk_size // 2 because rfind
                           searches for split points in [pos + chunk_size // 2, end],
                           so any chunk clearing that window is within spec.
                           Short-paragraph documents (e.g. annual reports)
                           legitimately produce chunks near the lower bound
                           when rfind finds a paragraph boundary early in
                           the search window.
    """
    chunk_size = processor.chunk_size
    lower = chunk_size // 2  # 250 — rfind search window lower bound
    upper = chunk_size       # 500

    _, chunks = processor.process(str(sample_pdf), doc_id="test-doc")
    assert chunks

    lengths = [len(c.text) for c in chunks]

    # Hard lower bound — all chunks must pass the filter
    min_len = min(lengths)
    assert min_len >= 10, f"Chunk shorter than 10 chars found: {min_len}"

    # Hard upper bound — paragraph boundary may slightly overshoot chunk_size
    max_len = max(lengths)
    assert max_len <= chunk_size + 50, (
        f"Chunk too long ({max_len} chars) — expected <= {chunk_size + 50}"
    )

    # Identify "last chunk of each page" — these are allowed to be short
    last_of_page_indices: set[int] = set()
    for i in range(len(chunks) - 1):
        if chunks[i].page_number != chunks[i + 1].page_number:
            last_of_page_indices.add(i)
    last_of_page_indices.add(len(chunks) - 1)  # also exclude the very last chunk

    middle_lengths = [
        l for i, l in enumerate(lengths) if i not in last_of_page_indices
    ]

    # Soft threshold — strict 85% requirement on middle chunks only
    if middle_lengths:
        in_range = sum(1 for l in middle_lengths if lower <= l <= upper)
        ratio = in_range / len(middle_lengths)
        assert ratio >= 0.85, (
            f"Only {ratio:.0%} of middle chunks are in [{lower}, {upper}] chars — "
            f"expected at least 85%. Total chunks={len(chunks)}, "
            f"middle={len(middle_lengths)}, tails excluded={len(last_of_page_indices)}"
        )


# ---------------------------------------------------------------------------
# e) doc_id 传播到所有 chunk
# ---------------------------------------------------------------------------

def test_doc_id_propagated(processor: PDFProcessor, sample_pdf: Path) -> None:
    """Every chunk must carry the doc_id passed to process()."""
    doc_id = "my-test-doc-uuid"
    _, chunks = processor.process(str(sample_pdf), doc_id=doc_id)
    assert chunks
    assert all(c.doc_id == doc_id for c in chunks), (
        "Some chunks have incorrect doc_id"
    )


# ---------------------------------------------------------------------------
# f) 单页无文字 PDF 返回 page_count=1，chunks=[]，不抛异常
# ---------------------------------------------------------------------------

def test_pdf_with_no_text_content_returns_empty_chunks(processor: PDFProcessor) -> None:
    """process() on a PDF with pages but no text must return (1, []) without raising."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    try:
        doc = fitz.open()
        doc.new_page()        # one blank page, no text blocks
        doc.save(tmp_path)
        doc.close()

        page_count, chunks = processor.process(tmp_path, doc_id="empty")
        assert page_count == 1
        assert chunks == []
    finally:
        Path(tmp_path).unlink(missing_ok=True)
