"""
PDF text extraction and chunking service.

Pipeline: PDF → get_text("blocks") → (y, x) 排序 → 段落分块
每个 Chunk 保留 page_number,确保答案可追溯。

排序假设: 单栏排版。多栏 PDF 会文字乱序——见 CLAUDE.md 明确不做。
表格页: 同行单元格按 x 顺序连在一起,接受语义部分损失。
"""
from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int  # 文档级全局索引,跨页连续,Step 3 用作 Chroma ID
    doc_id: str


class PDFProcessor:
    """Extract text from PDF and split into overlapping chunks with page metadata."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        """
        Args:
            chunk_size:    Target chunk length in characters (from settings.chunk_size).
            chunk_overlap: Overlap between consecutive chunks (from settings.chunk_overlap).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _extract_page_text(self, page: fitz.Page) -> str:
        """
        Extract text from a single page, sorted by reading order (y then x).

        Filters out image blocks (block_type != 0) and empty blocks.
        Joins remaining block texts with newlines.

        Args:
            page: A fitz.Page object.

        Returns:
            Page text as a single string, blocks joined by newline.
        """
        blocks = page.get_text("blocks")
        text_blocks = sorted(
            [b for b in blocks if b[6] == 0 and b[4].strip()],
            key=lambda b: (b[1], b[0]),  # sort by (y0, x0)
        )
        return "\n".join(b[4].strip() for b in text_blocks)

    def _chunk_text(
        self,
        text: str,
        page_number: int,
        doc_id: str,
        start_chunk_index: int,
    ) -> list[Chunk]:
        """
        Split page text into overlapping chunks.

        Split priority: double-newline paragraph boundary > sentence-ending
        punctuation (。!?;\\n) > hard cut at chunk_size.

        Chunks shorter than 10 characters after stripping are discarded.

        Args:
            text:              Full text of one page.
            page_number:       1-indexed page number.
            doc_id:            Document UUID.
            start_chunk_index: Global chunk index to begin from for this page.

        Returns:
            List of Chunk objects for this page.
        """
        chunks: list[Chunk] = []
        pos = 0
        chunk_idx = start_chunk_index

        while pos < len(text):
            end = pos + self.chunk_size

            if end >= len(text):
                chunk_text = text[pos:]
                pos = len(text)
            else:
                # Priority 1: paragraph boundary (double newline) in back half
                split = text.rfind("\n\n", pos + self.chunk_size // 2, end)
                if split > pos:
                    end = split + 2
                else:
                    # Priority 2: sentence-ending punctuation in back half
                    for punct in "。!?;\n":
                        split = text.rfind(punct, pos + self.chunk_size // 2, end)
                        if split > pos:
                            end = split + 1
                            break
                    # Priority 3: hard cut (end unchanged)

                chunk_text = text[pos:end]
                # Prevent infinite loop: ensure pos always advances by at least 1
                pos = max(end - self.chunk_overlap, pos + 1)

            if len(chunk_text.strip()) >= 10:
                chunks.append(
                    Chunk(
                        text=chunk_text.strip(),
                        page_number=page_number,
                        chunk_index=chunk_idx,
                        doc_id=doc_id,
                    )
                )
                chunk_idx += 1

        return chunks

    def process(self, pdf_path: str, doc_id: str) -> tuple[int, list[Chunk]]:
        """
        Extract text from a PDF and split into chunks.

        Args:
            pdf_path: Absolute path to the PDF file.
            doc_id:   Document UUID from the documents table.

        Returns:
            Tuple of (page_count, chunks) where page_count is the total number
            of pages in the PDF and chunks is an ordered list of Chunk objects
            with globally continuous chunk_index values.
        """
        all_chunks: list[Chunk] = []
        global_idx = 0

        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1  # convert to 1-indexed
                text = self._extract_page_text(page)
                if not text.strip():
                    continue  # skip empty pages; page_count still includes them
                page_chunks = self._chunk_text(
                    text,
                    page_number=page_num,
                    doc_id=doc_id,
                    start_chunk_index=global_idx,
                )
                all_chunks.extend(page_chunks)
                global_idx += len(page_chunks)

        return page_count, all_chunks
