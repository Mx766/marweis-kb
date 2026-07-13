import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


# ─────────────────────────────────────────────────────
# Determine the project root (two levels up from this file)
# ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────
    APP_NAME: str = "迈瑞生知识库"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production"] = "development"

    # ── Database ───────────────────────────────────────
    DATABASE_URL: str = (
        f"postgresql+asyncpg://"
        f"{os.getenv('DB_USER', 'marweis')}:{os.getenv('DB_PASSWORD', 'change-me')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME', 'marweis_kb')}"
    )

    # ── JWT ────────────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-use-random-string")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    # ── Meilisearch ────────────────────────────────────
    MEILI_URL: str = os.getenv("MEILI_URL", "http://localhost:7700")
    MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "change-me")

    # ── MinIO ──────────────────────────────────────────
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "change-me")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "change-me")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "marweis-documents")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # ── Gotenberg ──────────────────────────────────────
    GOTENBERG_URL: str = os.getenv("GOTENBERG_URL", "http://localhost:3000")

    # ── File upload ────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_EXTENSIONS: set[str] = {
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "txt", "md", "csv", "json",
        "jpg", "jpeg", "png", "gif", "tiff", "tif", "bmp",
        "mp4", "avi", "mov", "wmv", "mp3", "wav", "wma", "flac",
        "zip", "rar", "7z",
        "dwg", "dxf", "stp", "step",
        "dcm", "nrrd",
        "epub", "mobi",
    }

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()

DEPARTMENTS = [
    "器械注册部",
    "临床评价部",
    "临床试验部",
    "生产体系部",
    "化妆品·医美部",
    "特医食品部",
    "管理层",
]

ROLES = [
    "super_admin",
    "dept_admin",
    "editor",
    "employee",
    "guest",
]
