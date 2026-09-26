"""
Routes cho phân hệ Market Intelligence Analysis.

Endpoints:
  POST /api/analyze        → Tạo job, kick off background task, trả job_id
  GET  /api/stream/{job_id} → SSE stream tiến trình job
  GET  /api/jobs/{job_id}   → REST fallback để poll trạng thái job
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    JobStatus,
    JobStatusResponse,
)
from app.services.analysis_service import (
    create_job,
    get_job,
    run_analysis_pipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Market Intelligence"])


# ---------------------------------------------------------------------------
# POST /api/analyze — Khởi tạo job và chạy pipeline trong background
# ---------------------------------------------------------------------------

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Khởi tạo Market Intelligence analysis job",
    description=(
        "Nhận query, tạo job_id, kick off background task (Tavily + Gemini). "
        "Client dùng stream_url để kết nối SSE và nhận progress real-time."
    ),
)
async def start_analysis(
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    job_id = create_job(payload.query)

    # ⚡ Thêm pipeline vào background — KHÔNG await, không block response
    background_tasks.add_task(
        run_analysis_pipeline,
        job_id=job_id,
        query=payload.query,
        max_results=payload.max_results,
    )

    return AnalyzeResponse(
        job_id=job_id,
        stream_url=f"/api/stream/{job_id}",
    )


# ---------------------------------------------------------------------------
# GET /api/stream/{job_id} — SSE endpoint stream tiến trình
# ---------------------------------------------------------------------------

async def _sse_generator(job_id: str, request: Request):
    """
    Async generator tạo SSE events từ jobs_db.

    Vòng lặp polling:
      - Đọc trạng thái job từ jobs_db (in-memory, cực nhanh)
      - Gửi event "progress" hoặc "completed"/"failed"
      - yield control sau mỗi lần gửi (await asyncio.sleep)
      - Thoát ngay khi client disconnect hoặc job về trạng thái cuối

    Format SSE chuẩn (RFC 8895):
      data: <json>\n\n
    """
    POLL_INTERVAL = 0.5  # Giây — cân bằng giữa responsiveness và CPU usage
    MAX_WAIT_SECONDS = 300  # 5 phút timeout tối đa

    elapsed = 0.0

    while elapsed < MAX_WAIT_SECONDS:
        # Kiểm tra client có còn kết nối không (tránh lãng phí resource)
        if await request.is_disconnected():
            logger.info("SSE client disconnected cho job=%s", job_id)
            return

        job = get_job(job_id)
        if job is None:
            # Job không tồn tại — có thể server restart, báo lỗi
            error_payload = json.dumps({
                "status": "failed",
                "progress": 0,
                "message": f"Job {job_id} không tồn tại.",
                "error": "JOB_NOT_FOUND",
                "result": None,
            })
            yield f"data: {error_payload}\n\n"
            return

        payload = {
            "status": job.status.value,
            "progress": job.progress,
            "message": job.message,
            "result": job.result,
            "error": job.error,
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # Job đã về trạng thái cuối — đóng stream
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            logger.info("SSE stream kết thúc cho job=%s (status=%s)", job_id, job.status)
            return

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — báo cho client biết
    timeout_payload = json.dumps({
        "status": "failed",
        "progress": 0,
        "message": "Job timeout sau 5 phút. Vui lòng thử lại.",
        "error": "TIMEOUT",
        "result": None,
    })
    yield f"data: {timeout_payload}\n\n"


@router.get(
    "/stream/{job_id}",
    summary="SSE stream tiến trình analysis job",
    description=(
        "Server-Sent Events endpoint. Client kết nối bằng native EventSource API. "
        "Stream tự đóng khi job về trạng thái 'completed' hoặc 'failed'."
    ),
    response_class=StreamingResponse,
)
async def stream_job_progress(job_id: str, request: Request) -> StreamingResponse:
    # Validate job tồn tại trước khi stream
    if get_job(job_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id!r} không tồn tại.",
        )

    return StreamingResponse(
        _sse_generator(job_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Tắt Nginx buffering nếu có reverse proxy
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id} — REST fallback polling
# ---------------------------------------------------------------------------

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Lấy trạng thái job (REST fallback)",
    description="Dự phòng cho môi trường không hỗ trợ SSE — poll định kỳ.",
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id!r} không tồn tại.",
        )
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
    )
