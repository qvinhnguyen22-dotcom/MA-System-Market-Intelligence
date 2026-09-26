"""Tìm kiếm web thời gian thực qua Tavily — chạy sync, gọi từ asyncio.to_thread."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def search_market_intelligence(product_name: str) -> dict[str, Any]:
    """
    Cào dữ liệu web cho sản phẩm. Không raise ra ngoài trừ lỗi cấu hình thiếu key;
    lỗi mạng được gói vào dict để pipeline vẫn tiếp tục sang Gemini.
    """
    if not settings.TAVILY_API_KEY:
        raise RuntimeError("Thiếu TAVILY_API_KEY trong biến môi trường.")

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    query = (
        f"Phân tích thị trường {product_name} Việt Nam 2024 2025: "
        "đối thủ cạnh tranh, xu hướng, chân dung khách hàng, SWOT"
    )

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=8,
            include_answer=True,
        )
    except Exception as exc:
        logger.exception("Tavily search thất bại")
        return {
            "query": query,
            "answer": "",
            "results": [],
            "error": str(exc),
        }

    results = []
    for item in response.get("results") or []:
        results.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": (item.get("content") or "")[:2500],
            }
        )

    return {
        "query": query,
        "answer": response.get("answer") or "",
        "results": results,
        "error": None,
    }


def format_research_context(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    if payload.get("answer"):
        lines.append(f"Tóm tắt Tavily: {payload['answer']}")
    if payload.get("error"):
        lines.append(f"(Tavily lỗi: {payload['error']})")
    for index, item in enumerate(payload.get("results") or [], start=1):
        lines.append(
            f"[{index}] {item.get('title')}\nURL: {item.get('url')}\n{item.get('content')}"
        )
    return "\n\n".join(lines) if lines else "Không có dữ liệu web."
