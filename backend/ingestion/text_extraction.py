import pymupdf
import pymupdf4llm
import hashlib
from typing import Dict, List, Optional


class PDFExtractionError(Exception):
    pass


def _block_id(doc_id: str, page: int, text: str) -> str:
    """
    Deterministic ID for re-indexing, audit, dedup
    """
    h = hashlib.sha256()
    h.update(f"{doc_id}:{page}:{text}".encode("utf-8"))
    return h.hexdigest()


def extract_pdf_llm_blocks(
    pdf_path: str,
    doc_id: str,
    doc_name: str,
    password: Optional[str] = None
) -> Dict:
    """
    Canonical RakshaKosh PDF extraction using PyMuPDF + pymupdf4llm

    ❌ No chunking
    ❌ No embeddings
    ❌ No vector DB
    ❌ No disk writes

    ✅ Layout aware
    ✅ Table aware
    ✅ Offline
    """

    try:
        doc = pymupdf.open(pdf_path)

        # Handle encrypted PDFs
        if doc.is_encrypted:
            if not password:
                raise PDFExtractionError("Encrypted PDF but no password provided")

            if not doc.authenticate(password):
                raise PDFExtractionError("Invalid PDF password")

        blocks: List[Dict] = []
        total_pages = len(doc)

        for page_index in range(total_pages):
            page = doc[page_index]

            # 🔑 Core extraction (markdown, tables preserved)
            md_text = pymupdf4llm.to_markdown(
                page,
                write_images=False,
                margins=(0, 50, 0, 50)
            ).strip()

            if not md_text:
                continue

            block_type = "table" if _looks_like_table(md_text) else "prose"

            blocks.append({
                "block_id": _block_id(doc_id, page_index + 1, md_text),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page_num": page_index + 1,
                "type": block_type,
                "text": md_text
            })

        doc.close()

        return {
            "engine": "pymupdf4llm",
            "doc_id": doc_id,
            "doc_name": doc_name,
            "total_pages": total_pages,
            "blocks": blocks
        }

    except Exception as e:
        raise PDFExtractionError(
            f"Extraction failed for {pdf_path}: {str(e)}"
        ) from e


def _looks_like_table(text: str) -> bool:
    """
    Conservative markdown table detection
    """
    lines = text.splitlines()
    pipe_lines = [l for l in lines if "|" in l]
    separator = any("---" in l for l in lines)

    return len(pipe_lines) >= 2 and separator
