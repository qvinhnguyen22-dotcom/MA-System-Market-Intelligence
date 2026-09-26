"""
Pipeline phân tích bất đồng bộ.

Tavily/Gemini là I/O sync — luôn chạy qua asyncio.to_thread để không chặn
event loop (SSE vẫn đẩy progress 20% → 60% → 100%).
"""

from __future__ import annotations

import asyncio
import logging

from app.core.jobs import update_job
from app.services.analysis_service import generate_market_analysis
from app.services.tavily_service import format_research_context, search_market_intelligence

logger = logging.getLogger(__name__)


async def run_analysis_job(job_id: str, product_name: str) -> None:
    try:
        update_job(
            job_id,
            status="in_progress",
            progress=20,
            message="Đang cào dữ liệu web thời gian thực (Tavily)...",
        )
        research = await asyncio.to_thread(search_market_intelligence, product_name)
        context = format_research_context(research)

        update_job(
            job_id,
            status="in_progress",
            progress=60,
            message="Gemini 2.0 Flash đang tổng hợp SWOT và báo cáo chiến lược...",
        )
        result = await asyncio.to_thread(
            generate_market_analysis, product_name, context
        )

        update_job(
            job_id,
            status="in_progress",
            progress=90,
            message="Đang chuẩn hóa kết quả JSON...",
        )
        update_job(
            job_id,
            status="completed",
            progress=100,
            message="Hoàn tất tổng hợp báo cáo chiến lược!",
            result=result,
            error=None,
        )
    except Exception as exc:
        logger.exception("Job %s thất bại", job_id)
        update_job(
            job_id,
            status="failed",
            progress=100,
            message=f"Thất bại: {exc}",
            error=str(exc),
        )
