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
    DB_USER: str = "marweis"
    DB_PASSWORD: str = "change-me"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "marweis_kb"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}"
            f"/{self.DB_NAME}"
        )

    # ── JWT ────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production-use-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    # ── Meilisearch ────────────────────────────────────
    MEILI_URL: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str = "change-me"

    # ── MinIO ──────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str = ""  # 公网访问地址，留空则等于 MINIO_ENDPOINT
    MINIO_ACCESS_KEY: str = "change-me"
    MINIO_SECRET_KEY: str = "change-me"
    MINIO_BUCKET: str = "marweis-documents"
    MINIO_SECURE: bool = False
    MINIO_PRESIGNED_EXPIRES: int = 3600  # 预签名 URL 有效期(秒)

    # ── Gotenberg ──────────────────────────────────────
    GOTENBERG_URL: str = "http://localhost:3000"

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
