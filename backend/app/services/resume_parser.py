"""
Service trích xuất text thô từ file CV (PDF / DOCX).

Đây là bước tiền xử lý (pre-processing) trước khi gọi LLM:
- Chấm điểm ATS
- Phân tích điểm mạnh/yếu
- Gợi ý viết lại Summary / Experience
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from enum import Enum

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class ResumeFileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


@dataclass(frozen=True)
class ParsedResume:
    """Kết quả nội bộ sau khi parse file CV."""

    file_type: ResumeFileType
    text: str
    page_count: int | None = None


class ResumeParserError(Exception):
    """Lỗi nghiệp vụ khi không thể đọc hoặc trích xuất CV."""


def _normalize_text(raw: str) -> str:
    """
    Chuẩn hóa text thô:
    - Gộp nhiều dòng trống liên tiếp
    - Loại bỏ khoảng trắng thừa ở đầu/cuối dòng
    """
    lines = [line.strip() for line in raw.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_from_pdf(content: bytes) -> ParsedResume:
    """Đọc text từ PDF bằng pypdf (hỗ trợ multi-page)."""
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ResumeParserError("Không thể mở file PDF. File có thể bị hỏng hoặc mã hóa.") from exc

    if len(reader.pages) == 0:
        raise ResumeParserError("File PDF không có trang nào.")

    page_texts: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Không trích xuất được trang PDF index=%s: %s", index, exc)
            page_text = ""
        page_texts.append(page_text)

    combined = _normalize_text("\n".join(page_texts))
    if not combined:
        raise ResumeParserError(
            "PDF không chứa text có thể đọc được. "
            "Có thể đây là file scan ảnh — cần OCR ở phase sau."
        )

    return ParsedResume(
        file_type=ResumeFileType.PDF,
        text=combined,
        page_count=len(reader.pages),
    )


def _extract_from_docx(content: bytes) -> ParsedResume:
    """Đọc text từ DOCX: paragraphs + tables (CV thường dùng bảng cho layout)."""
    try:
        document = Document(io.BytesIO(content))
    except Exception as exc:
        raise ResumeParserError("Không thể mở file DOCX. File có thể bị hỏng.") from exc

    chunks: list[str] = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            chunks.append(paragraph.text.strip())

    # Một số CV dùng table thay vì paragraph thuần
    for table in document.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                chunks.append(" | ".join(row_cells))

    combined = _normalize_text("\n".join(chunks))
    if not combined:
        raise ResumeParserError("File DOCX không chứa nội dung text.")

    return ParsedResume(
        file_type=ResumeFileType.DOCX,
        text=combined,
        page_count=None,
    )


def parse_resume(content: bytes, file_type: ResumeFileType) -> ParsedResume:
    """
    Entry point: nhận bytes + loại file, trả về ParsedResume.

    Raises:
        ResumeParserError: Khi file không đọc được hoặc không có text.
    """
    if file_type == ResumeFileType.PDF:
        return _extract_from_pdf(content)
    if file_type == ResumeFileType.DOCX:
        return _extract_from_docx(content)

    raise ResumeParserError(f"Loại file không được hỗ trợ: {file_type}")


def count_words(text: str) -> int:
    """Đếm số từ đơn giản — đủ dùng cho metadata MVP."""
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))
