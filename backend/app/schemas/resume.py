"""
Pydantic schemas cho phân hệ Resume / CV.
Tách riêng khỏi logic xử lý để dễ tái sử dụng và validate response API.
"""

from pydantic import BaseModel, Field


class ResumeMetadata(BaseModel):
    """Metadata kỹ thuật của file CV sau khi parse."""

    filename: str = Field(..., description="Tên file gốc do client upload")
    file_type: str = Field(..., description="Loại file: pdf | docx")
    file_size_bytes: int = Field(..., ge=0, description="Kích thước file (bytes)")
    page_count: int | None = Field(
        default=None,
        description="Số trang (chỉ áp dụng PDF; DOCX trả về null)",
    )
    character_count: int = Field(..., ge=0, description="Tổng số ký tự text trích xuất")
    word_count: int = Field(..., ge=0, description="Ước lượng số từ trong text")


class ResumeExtractResponse(BaseModel):
    """
    Response sau bước trích xuất text thô.
    `extracted_text` sẽ được đưa vào LLM ở bước ATS scoring / rewrite tiếp theo.
    """

    success: bool = True
    message: str = "Trích xuất text từ CV thành công."
    metadata: ResumeMetadata
    extracted_text: str = Field(..., description="Nội dung text thô từ CV")
