"""
API endpoints cho phân hệ AI Resume Reviewer (MVP).

Flow hiện tại:
  Upload CV (.pdf / .docx) → Trích xuất text thô → Trả về cho client / bước LLM tiếp theo
"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.resume import ResumeExtractResponse, ResumeMetadata
from app.services.resume_parser import (
    ResumeFileType,
    ResumeParserError,
    count_words,
    parse_resume,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])


def _resolve_file_type(filename: str | None, content_type: str | None) -> ResumeFileType:
    """
    Xác định loại file từ extension (ưu tiên) và MIME type (fallback).
    Tránh trust hoàn toàn Content-Type do client có thể gửi sai.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên file không hợp lệ.",
        )

    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return ResumeFileType.PDF
    if extension == ".docx":
        return ResumeFileType.DOCX

    # Fallback MIME nếu extension lạ nhưng MIME đúng
    if content_type in settings.ALLOWED_RESUME_MIME_TYPES:
        if "pdf" in content_type:
            return ResumeFileType.PDF
        return ResumeFileType.DOCX

    allowed = ", ".join(sorted(settings.ALLOWED_RESUME_EXTENSIONS))
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Chỉ hỗ trợ file: {allowed}",
    )


@router.post(
    "/upload",
    response_model=ResumeExtractResponse,
    summary="Upload CV và trích xuất text thô",
    description=(
        "Nhận file PDF hoặc DOCX, trích xuất nội dung text để chuẩn bị "
        "cho bước phân tích ATS / gọi LLM."
    ),
)
async def upload_and_extract_resume(
    file: UploadFile = File(..., description="File CV (.pdf hoặc .docx)"),
) -> ResumeExtractResponse:
    file_type = _resolve_file_type(file.filename, file.content_type)

    # Đọc nội dung vào memory (MVP); phase sau có thể stream + lưu S3/MinIO
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File rỗng.",
        )

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File vượt quá giới hạn {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    try:
        parsed = parse_resume(content, file_type)
    except ResumeParserError as exc:
        logger.warning("Parse CV thất bại (%s): %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Lỗi không mong đợi khi parse CV: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể xử lý file CV. Vui lòng thử lại.",
        ) from exc

    metadata = ResumeMetadata(
        filename=file.filename or "unknown",
        file_type=parsed.file_type.value,
        file_size_bytes=file_size,
        page_count=parsed.page_count,
        character_count=len(parsed.text),
        word_count=count_words(parsed.text),
    )

    return ResumeExtractResponse(
        metadata=metadata,
        extracted_text=parsed.text,
    )
