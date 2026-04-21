"""
PDF text extraction and chunking service.

Implemented in Step 2. Stub only.

Pipeline: PDF → get_text("blocks") → 多栏坐标排序 → 段落分块
每个 Chunk 保留 page_number，确保答案可追溯。
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int
    doc_id: str


class PDFProcessor:
    """Extract text from PDF and split into chunks with page metadata."""

    def process(self, pdf_path: str, doc_id: str) -> list[Chunk]:
        """
        Extract and chunk a PDF file.

        Args:
            pdf_path: Absolute path to the PDF file.
            doc_id:   Document UUID from the documents table.

        Returns:
            Ordered list of Chunks with text, page_number, chunk_index, doc_id.
        """
        raise NotImplementedError("Implemented in Step 2")
