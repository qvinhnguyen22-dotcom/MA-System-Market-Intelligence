"""
Entry point FastAPI — AMA-System Market Intelligence Backend.

Chạy development server:
    uvicorn main:app --reload --host 127.0.0.1 --port 8000

Hoặc:
    python main.py
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, resume
from app.api.routes.analyze import router as analyze_router
from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Hook khởi động / tắt app."""
    # Startup
    logger.info("🚀 %s v%s khởi động", settings.APP_NAME, settings.APP_VERSION)
    if not settings.GEMINI_API_KEY:
        logger.warning("⚠️  GEMINI_API_KEY chưa được cấu hình!")
    if not settings.TAVILY_API_KEY:
        logger.warning("⚠️  TAVILY_API_KEY chưa được cấu hình!")
    logger.info("CORS_ORIGINS: %s", settings.CORS_ORIGINS)
    yield
    # Shutdown
    logger.info("👋 Server đang tắt...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API cho AMA-System Market Intelligence — "
        "phân tích thị trường real-time bằng Tavily + Gemini 2.0 Flash."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────
# allow_origins đọc trực tiếp từ settings.CORS_ORIGINS (đã parse từ .env)
# Đảm bảo không bao giờ hard-code — thêm origin mới vào .env: CORS_ORIGINS=...,neworigin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Cần cho SSE nếu có custom headers
)

# ── Routers ───────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"

# Legacy resume routes
app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(resume.router, prefix=API_V1_PREFIX)

# Market Intelligence routes (prefix /api đã được định nghĩa trong router)
app.include_router(analyze_router)


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Redirect info — trỏ dev tới Swagger UI."""
    return {
        "message": "AMA-System Market Intelligence API",
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
        "analyze": "/api/analyze",
        "stream": "/api/stream/{job_id}",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
    )
