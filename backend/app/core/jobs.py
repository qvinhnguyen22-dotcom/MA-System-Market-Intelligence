"""
In-memory job store dùng chung giữa POST /api/analyze và SSE /api/stream.

Lưu ý MVP: dict này sống theo process. Chạy 1 worker uvicorn (không --workers > 1)
để tránh mất trạng thái job khi request rơi sang process khác.
"""

from __future__ import annotations

import copy
import threading
from typing import Any

jobs_db: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def create_job(job_id: str, product_name: str) -> dict[str, Any]:
    job: dict[str, Any] = {
        "job_id": job_id,
        "product_name": product_name,
        "status": "in_progress",
        "progress": 5,
        "message": "Khởi tạo tiến trình phân tích thị trường...",
        "result": None,
        "error": None,
    }
    with _jobs_lock:
        jobs_db[job_id] = job
        return copy.deepcopy(job)


def update_job(job_id: str, **fields: Any) -> dict[str, Any] | None:
    with _jobs_lock:
        job = jobs_db.get(job_id)
        if job is None:
            return None
        job.update(fields)
        return copy.deepcopy(job)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = jobs_db.get(job_id)
        return copy.deepcopy(job) if job is not None else None
