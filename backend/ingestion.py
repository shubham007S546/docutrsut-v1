from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from typing import Any

from backend.config import settings

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


@dataclass(frozen=True)
class IngestedChunk:
    index: int
    content: str
    char_start: int
    char_end: int
    page_start: int | None = 1
    page_end: int | None = 1
    section: str = "General"
    chunk_id: str | None = None


@dataclass(frozen=True)
class IngestedDocument:
    sha256: str
    mime_type: str
    chunks: list[IngestedChunk]
    total_pages: int = 1
    extracted_text: str = ""


class IngestionError(ValueError):
    pass


def validate_upload(filename: str, mime_type: str, content: bytes) -> None:
    """Validates file presence, size limits, allowed MIME types, and basic content integrity."""
    if not filename or not filename.strip() or filename.strip().startswith("."):
        raise IngestionError("A safe filename is required")

    if len(content) == 0:
        raise IngestionError("Uploaded file is empty (0 bytes)")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise IngestionError(f"Upload exceeds {settings.max_upload_mb} MB limit")

    norm_mime = mime_type.lower().split(";")[0].strip()
    if norm_mime not in ALLOWED_MIME_TYPES:
        raise IngestionError("Unsupported document type")

    # Magic byte verification to prevent MIME spoofing
    if norm_mime == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise IngestionError("Corrupted or invalid PDF header")
    elif norm_mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        if not (content.startswith(b"PK\x03\x04") or content.startswith(b"\xd0\xcf\x11\xe0")):
            raise IngestionError("Corrupted or invalid Microsoft Office document header")


def extract_section_title(text: str) -> str:
    """Extracts the first matching section header (e.g. 'Section 4.2: Work-From-Home Limitations') from a text block."""
    for line in text.splitlines():
        line_s = line.strip()
        if re.match(r"^(section\s+\d+(\.\d+)?|article\s+\d+|clause\s+\d+|chapter\s+\d+)", line_s, re.IGNORECASE):
            return line_s.split(":")[0].strip() if ":" in line_s else line_s[:50].strip()
    return "General"


def chunk_page_text(
    pages: list[tuple[int, str]],
    target_chars: int | None = None,
    overlap: int | None = None,
) -> list[IngestedChunk]:
    """Splits page-delimited text into chunks while accurately preserving original page numbers and section headers."""
    target_chars = target_chars or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    chunks: list[IngestedChunk] = []
    global_char_offset = 0

    for page_num, raw_content in pages:
        normalized = re.sub(r"\r\n?", "\n", raw_content).strip()
        if not normalized:
            continue

        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + target_chars)
            if end < len(normalized):
                # Search for a natural boundary: paragraph break or sentence end
                boundary = normalized.rfind("\n\n", start, end)
                if boundary == -1 or boundary <= start + target_chars // 3:
                    boundary = normalized.rfind("\n", start, end)
                if boundary == -1 or boundary <= start + target_chars // 3:
                    boundary = normalized.rfind(". ", start, end)
                    if boundary != -1:
                        boundary += 1

                if boundary > start + target_chars // 3:
                    end = boundary

            chunk_content = normalized[start:end].strip()
            if len(chunk_content) >= 15:
                section = extract_section_title(chunk_content)
                c_start = global_char_offset + start
                c_end = global_char_offset + end
                chunk_obj = IngestedChunk(
                    index=len(chunks),
                    content=chunk_content,
                    char_start=c_start,
                    char_end=c_end,
                    page_start=page_num,
                    page_end=page_num,
                    section=section,
                    chunk_id=f"chunk_p{page_num}_{len(chunks)}",
                )
                chunks.append(chunk_obj)

            if end == len(normalized):
                break
            start = max(end - overlap, start + 1)

        global_char_offset += len(normalized) + 2

    return chunks


def extract_pdf_pages(content: bytes) -> list[tuple[int, str]]:
    """Extracts text page-by-page from PDF bytes using PyMuPDF and pdfplumber fallbacks."""
    pages: list[tuple[int, str]] = []

    # 1. Primary: PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        if doc.is_encrypted:
            raise IngestionError("Encrypted PDF files are not supported without password credentials")

        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((idx, text))
    except IngestionError:
        raise
    except Exception as err:
        pass

    # 2. Secondary fallback: pdfplumber
    if not pages:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append((idx, text.strip()))
        except Exception:
            pass

    return pages


def extract_docx_text(content: bytes) -> list[tuple[int, str]]:
    """Extracts text and tables from DOCX bytes using python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        elements: list[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                elements.append(text)

        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    elements.append(" | ".join(row_cells))

        full_text = "\n\n".join(elements).strip()
        return [(1, full_text)] if full_text else []
    except Exception as err:
        raise IngestionError(f"Failed to parse DOCX document: {err}") from err


def prepare_text_document(
    filename: str,
    mime_type: str,
    content: bytes,
    target_chars: int | None = None,
    overlap: int | None = None,
) -> IngestedDocument:
    """End-to-end ingestion pipeline: validates upload, extracts text per page, cleans noise, and chunks with metadata."""
    validate_upload(filename, mime_type, content)
    norm_mime = mime_type.lower().split(";")[0].strip()

    pages: list[tuple[int, str]] = []

    if norm_mime == "application/pdf":
        pages = extract_pdf_pages(content)
        if not pages:
            raise IngestionError(
                "This PDF could not be read or contains no searchable text layer. It may be scanned and require OCR."
            )

    elif norm_mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        pages = extract_docx_text(content)
        if not pages:
            raise IngestionError("The Word document contains no readable text content.")

    else:
        # Plain text, Markdown, JSON, CSV
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    raw_text = content.decode("latin-1")
                except UnicodeDecodeError as err:
                    raise IngestionError("This document could not be decoded safely with UTF-8 or Latin-1") from err

        raw_text = raw_text.strip()
        if not raw_text:
            raise IngestionError("Document contains no extractable text")
        pages = [(1, raw_text)]

    # Clean text while preserving structural markers (headings, lists, section clauses)
    cleaned_pages: list[tuple[int, str]] = []
    for p_num, p_text in pages:
        # Remove null characters and control codes except newline and tab
        t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", p_text)
        # Collapse excessive newlines beyond 2
        t = re.sub(r"\n{3,}", "\n\n", t)
        cleaned_pages.append((p_num, t.strip()))

    chunks = chunk_page_text(cleaned_pages, target_chars=target_chars, overlap=overlap)
    if not chunks:
        raise IngestionError("Document contains no extractable text after chunking")

    sha256_hash = hashlib.sha256(content).hexdigest()
    total_pages = max((p[0] for p in cleaned_pages), default=1)
    extracted_full = "\n\n".join(p[1] for p in cleaned_pages)

    return IngestedDocument(
        sha256=sha256_hash,
        mime_type=norm_mime,
        chunks=chunks,
        total_pages=total_pages,
        extracted_text=extracted_full,
    )
