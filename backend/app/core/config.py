"""
Cấu hình tập trung cho toàn bộ ứng dụng.
Sử dụng biến môi trường từ file .env (không hard-code secrets).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    """Đọc và validate cấu hình runtime."""

    APP_NAME: str = "AMA-System Market Intelligence API"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS — frontend Next.js mặc định chạy port 3000
    # Đọc từ .env: CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    # Giới hạn upload CV (bytes)
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    ALLOWED_RESUME_EXTENSIONS: set[str] = {".pdf", ".docx"}
    ALLOWED_RESUME_MIME_TYPES: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    # ── Market Intelligence API Keys ──────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ── Legacy AI keys (cho phase Resume Review sau) ──────────────────────
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — cache để tránh đọc .env nhiều lần."""
    return Settings()


settings = get_settings()
