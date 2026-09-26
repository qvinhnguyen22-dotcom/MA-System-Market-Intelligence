"""
Pydantic v2 schemas cho phân hệ Market Intelligence Analysis.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Payload gửi từ Frontend để khởi tạo một analysis job."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Từ khóa / chủ đề Market Intelligence (VD: 'AI chip market 2024')",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Số kết quả Tavily tối đa (1-10)",
    )


# ---------------------------------------------------------------------------
# Internal Job model (in-memory)
# ---------------------------------------------------------------------------

class AnalysisJob(BaseModel):
    """Đại diện trạng thái của một analysis job trong jobs_db."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    message: str = "Đang khởi tạo..."
    result: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AnalyzeResponse(BaseModel):
    """Response ngay sau khi nhận POST /api/analyze — trả về job_id để poll SSE."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    message: str = "Job đã được tạo. Hãy kết nối SSE để theo dõi tiến trình."
    stream_url: str


class JobStatusResponse(BaseModel):
    """Response cho GET /api/jobs/{job_id} (optional REST polling)."""

    job_id: str
    status: JobStatus
    progress: int
    message: str
    result: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Gemini structured output schema
# ---------------------------------------------------------------------------

class MarketInsight(BaseModel):
    """Cấu trúc JSON Gemini phân tích trả về."""

    summary: str = Field(..., description="Tóm tắt thị trường (2-3 câu)")
    key_trends: list[str] = Field(default_factory=list, description="Các xu hướng chính")
    opportunities: list[str] = Field(default_factory=list, description="Cơ hội kinh doanh")
    risks: list[str] = Field(default_factory=list, description="Rủi ro cần chú ý")
    key_players: list[str] = Field(default_factory=list, description="Các tác nhân chính")
    market_size_estimate: str | None = Field(
        default=None, description="Ước tính quy mô thị trường nếu có"
    )


class AnalysisResult(BaseModel):
    """Kết quả phân tích hoàn chỉnh được lưu vào job.result."""

    query: str
    sources_count: int
    insights: MarketInsight
    report_markdown: str = Field(..., description="Báo cáo Markdown đầy đủ từ Gemini")
    sources: list[dict[str, str]] = Field(
        default_factory=list,
        description="Danh sách nguồn từ Tavily [{title, url, snippet}]",
    )
