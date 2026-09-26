"""
Analysis Service — Trái tim của Market Intelligence.

Pipeline:
  1. Tavily API → Cào dữ liệu web theo query (chạy non-blocking qua asyncio.to_thread)
  2. Gemini Flash AI → Phân tích structured JSON + báo cáo Markdown (auto-fallback models)
  3. Cập nhật jobs_db theo từng bước (progress 10% → 30% → 40% → 70% → 85% → 100%)
  4. Phục vụ Server-Sent Events (SSE) tại /api/stream/{job_id}

Bảo vệ cấp độ sản xuất:
  - Tất cả tác vụ I/O blocking (Tavily, Gemini) đều được offload sang worker threads bằng `asyncio.to_thread`
  - Đảm bảo Event Loop FastAPI KHÔNG bao giờ bị nghẽn
  - Parser JSON đa tầng (Multi-strategy) với regex khử trailing commas, unescaped chars
  - Tuyệt đối KHÔNG BAO GIỜ để crash tiến trình ngầm (tất cả exception được catch và set JobStatus.FAILED)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

import google.generativeai as genai
from tavily import TavilyClient

from app.core.config import settings
from app.schemas.analyze import (
    AnalysisJob,
    AnalysisResult,
    JobStatus,
    MarketInsight,
)

logger = logging.getLogger(__name__)

# Danh sách models Gemini theo thứ tự ưu tiên fallback
GEMINI_MODELS_FALLBACK = [
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-2.5-flash-lite",
]

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
# Key: job_id (UUID str)  →  Value: AnalysisJob
jobs_db: dict[str, AnalysisJob] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_job(job_id: str, **kwargs: Any) -> None:
    """Cập nhật fields của job trong jobs_db một cách an toàn."""
    job = jobs_db.get(job_id)
    if job is None:
        logger.error("_update_job: job_id=%s không tồn tại trong jobs_db", job_id)
        return
    updated = job.model_copy(update=kwargs)
    jobs_db[job_id] = updated


def _clean_json_string(raw: str) -> str:
    """Loại bỏ trailing commas và chuẩn hóa JSON string trước khi parse."""
    cleaned = raw.strip()
    # Loại bỏ trailing commas trước dấu } hoặc ]
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
    return cleaned


def _parse_json_from_gemini(text: str) -> dict[str, Any]:
    """
    Parse JSON từ Gemini response với 4 tầng chiến lược:
      1. JSON thuần
      2. Markdown code block ```json ... ```
      3. Bất kỳ markdown code block nào ``` ... ```
      4. Balanced curly braces extraction { ... }

    Nếu tất cả đều thất bại, trả về dict mặc định chứ KHÔNG raise exception
    để đảm bảo pipeline ngầm không bao giờ sập.
    """
    text = text.strip()

    # Tầng 1: Parse trực tiếp nếu bắt đầu bằng { hoặc [
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(_clean_json_string(text))
        except Exception:
            pass

    # Tầng 2: Extract từ ```json ... ``` block
    match_json = re.search(r"```json\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if match_json:
        candidate = _clean_json_string(match_json.group(1))
        try:
            return json.loads(candidate)
        except Exception as exc:
            logger.warning("Strategy 2 (```json block) parse warning: %s", exc)

    # Tầng 3: Extract từ bất kỳ ``` ... ``` block nào
    match_generic = re.search(r"```\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match_generic:
        candidate = _clean_json_string(match_generic.group(1))
        if candidate.startswith("{") or candidate.startswith("["):
            try:
                return json.loads(candidate)
            except Exception as exc:
                logger.warning("Strategy 3 (generic code block) parse warning: %s", exc)

    # Tầng 4: Balanced brace search (tìm JSON object lồng trong văn bản)
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i, ch in enumerate(text[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = _clean_json_string(text[brace_start : i + 1])
                    try:
                        return json.loads(candidate)
                    except Exception as exc:
                        logger.warning("Strategy 4 (brace extraction) parse warning: %s", exc)
                    break

    # Fallback an toàn: Trả về dict cơ bản thay vì crash
    logger.warning("Không thể parse JSON từ Gemini response, kích hoạt fallback an toàn.")
    return {
        "summary": "Không thể trích xuất tóm tắt JSON có cấu trúc. Vui lòng xem báo cáo chi tiết bên dưới.",
        "key_trends": [],
        "opportunities": [],
        "risks": [],
        "key_players": [],
        "market_size_estimate": None,
    }


def _build_gemini_prompt(query: str, sources_text: str) -> str:
    """Tạo prompt chuẩn hóa cho Gemini 2.0/Flash."""
    return f"""Bạn là chuyên gia phân tích thị trường & tình báo kinh doanh cấp cao (Senior Market Intelligence Analyst).
Dựa trên dữ liệu web thu thập được dưới đây, hãy thực hiện phân tích chuyên sâu cho chủ đề:

CHỦ ĐỀ (QUERY): {query}

DỮ LIỆU TÌM KIẾM WEB:
{sources_text}

---

YÊU CẦU ĐẦU RA: Bạn BẮT BUỘC phải chia câu trả lời làm 2 phần riêng biệt bằng dấu phân cách chính xác: ---REPORT---

PHẦN 1: Structured JSON (Chứa thông tin tóm tắt có cấu trúc)
```json
{{
  "summary": "Tóm tắt tổng quan thị trường trong 2-3 câu ngắn gọn, súc tích",
  "key_trends": ["Xu hướng 1", "Xu hướng 2", "Xu hướng 3"],
  "opportunities": ["Cơ hội 1", "Cơ hội 2"],
  "risks": ["Rủi ro / Thách thức 1", "Rủi ro / Thách thức 2"],
  "key_players": ["Tên công ty / Tổ chức 1", "Tên công ty / Tổ chức 2"],
  "market_size_estimate": "Ước tính quy mô / tốc độ tăng trưởng (hoặc null nếu không có số liệu)"
}}
```

---REPORT---

PHẦN 2: Báo cáo phân tích chuyên sâu bằng Markdown
Hãy viết báo cáo phân tích thị trường đầy đủ, trình bày rõ ràng và chuyên nghiệp bằng tiếng Việt:
# Báo Cáo Phân Tích Thị Trường: {query}
## 1. Tóm Tắt Điều Hành (Executive Summary)
## 2. Các Xu Hướng Phát Triển Đột Phá
## 3. Bản Đồ Cạnh Tranh & Tác Nhân Chính
## 4. Cơ Hội Đầu Tư & Kinh Doanh
## 5. Rủi Ro Tiềm Ẩn & Thách Thức
## 6. Đề Xuất Chiến Lược & Khuyến Nghị
"""


async def _generate_with_gemini(prompt: str) -> str:
    """
    Gọi Gemini API với cơ chế tự động fallback qua các model khả dụng.
    Chạy trong thread pool qua `asyncio.to_thread` để không block event loop.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    last_error: Exception | None = None

    for model_name in GEMINI_MODELS_FALLBACK:
        try:
            logger.info("Đang gọi Gemini model: %s", model_name)
            model = genai.GenerativeModel(model_name)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            if response and response.text:
                return response.text
        except Exception as exc:
            logger.warning("Gemini model %s gặp lỗi: %s. Thử model tiếp theo...", model_name, exc)
            last_error = exc

    raise RuntimeError(f"Tất cả các model Gemini đều thất bại. Lỗi cuối cùng: {last_error}")


# ---------------------------------------------------------------------------
# Core Analysis Pipeline (Chạy trong Background Task)
# ---------------------------------------------------------------------------

async def run_analysis_pipeline(job_id: str, query: str, max_results: int) -> None:
    """
    Quy trình xử lý phân tích dữ liệu thị trường:
      - Cào dữ liệu web qua Tavily
      - Phân tích và tạo báo cáo qua Gemini
      - Cập nhật tiến trình từng giai đoạn vào jobs_db
      - Luôn đảm bảo không bao giờ bị nghẽn Event Loop hoặc treo trạng thái job
    """
    try:
        # Giai đoạn 1: Khởi động & Cào dữ liệu Tavily (10% → 30%)
        _update_job(
            job_id,
            status=JobStatus.RUNNING,
            progress=10,
            message="🔍 Đang tìm kiếm và cào dữ liệu thị trường từ web...",
        )
        await asyncio.sleep(0)  # Yield cho Event Loop để SSE đẩy event 10% ngay

        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

        # Offload sync Tavily API call sang worker thread
        search_response = await asyncio.to_thread(
            tavily_client.search,
            query=query,
            max_results=max_results,
            include_raw_content=False,
            include_answer=True,
        )

        results = search_response.get("results", [])
        if not results:
            raise ValueError(f"Tavily không tìm thấy dữ liệu phù hợp cho từ khóa: {query!r}")

        sources = [
            {
                "title": r.get("title") or "Nguồn tham khảo",
                "url": r.get("url") or "",
                "snippet": (r.get("content") or "")[:600],
            }
            for r in results
        ]

        _update_job(
            job_id,
            progress=30,
            message=f"✅ Đã thu thập {len(sources)} nguồn dữ liệu. Chuẩn bị phân tích AI...",
        )
        await asyncio.sleep(0)

        # Giai đoạn 2: Chuẩn bị Prompt & Gọi Gemini (40% → 70%)
        _update_job(
            job_id,
            progress=40,
            message="🤖 Đang kích hoạt mô hình Gemini AI phân tích chuyên sâu...",
        )
        await asyncio.sleep(0)

        sources_text = "\n\n".join(
            f"[Nguồn {i+1}]: {s['title']}\nURL: {s['url']}\nTrích dẫn: {s['snippet']}"
            for i, s in enumerate(sources)
        )
        prompt = _build_gemini_prompt(query, sources_text)

        raw_text = await _generate_with_gemini(prompt)

        _update_job(
            job_id,
            progress=70,
            message="📊 Đang trích xuất dữ liệu cấu trúc và số liệu thị trường...",
        )
        await asyncio.sleep(0)

        # Giai đoạn 3: Phân tách JSON & Báo cáo Markdown (70% → 85%)
        separator = "---REPORT---"
        if separator in raw_text:
            parts = raw_text.split(separator, 1)
            json_part = parts[0].strip()
            report_markdown = parts[1].strip()
        else:
            # Fallback nếu model không tạo đúng separator
            match_fence = re.search(r"```json(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
            if match_fence:
                json_part = match_fence.group(0)
                # Báo cáo là phần văn bản sau khối json
                report_markdown = raw_text.replace(json_part, "").strip()
            else:
                json_part = raw_text
                report_markdown = raw_text

        insights_dict = _parse_json_from_gemini(json_part)

        # Tạo MarketInsight an toàn không throw ValidationError
        insights = MarketInsight(
            summary=insights_dict.get("summary") or f"Phân tích thị trường cho: {query}",
            key_trends=insights_dict.get("key_trends") or [],
            opportunities=insights_dict.get("opportunities") or [],
            risks=insights_dict.get("risks") or [],
            key_players=insights_dict.get("key_players") or [],
            market_size_estimate=insights_dict.get("market_size_estimate"),
        )

        _update_job(
            job_id,
            progress=85,
            message="📝 Đang hoàn thiện báo cáo và chuẩn hóa kết quả...",
        )
        await asyncio.sleep(0)

        # Giai đoạn 4: Hoàn tất & lưu kết quả (85% → 100%)
        final_report = report_markdown or f"# Báo Cáo Phân Tích: {query}\n\n{raw_text}"
        analysis_result = AnalysisResult(
            query=query,
            sources_count=len(sources),
            insights=insights,
            report_markdown=final_report,
            sources=sources,
        )

        _update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="✅ Phân tích hoàn tất thành công!",
            result=analysis_result.model_dump(),
        )
        logger.info("Job %s hoàn thành thành công (sources=%d)", job_id, len(sources))

    except Exception as exc:
        # Bắt toàn bộ ngoại lệ để job chuyển sang FAILED, tuyệt đối không treo tiến trình ngầm
        error_msg = str(exc)
        logger.exception("Job %s thất bại: %s", job_id, error_msg)
        _update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message=f"❌ Xử lý thất bại: {error_msg[:200]}",
            error=error_msg,
        )


# ---------------------------------------------------------------------------
# Public Functions
# ---------------------------------------------------------------------------

def create_job(query: str) -> str:
    """Tạo mới một Job trong memory jobs_db và trả về job_id UUID."""
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = AnalysisJob(job_id=job_id)
    logger.info("Đã tạo Job mới: %s (Query: %r)", job_id, query)
    return job_id


def get_job(job_id: str) -> AnalysisJob | None:
    """Lấy trạng thái hiện tại của job theo job_id."""
    return jobs_db.get(job_id)
