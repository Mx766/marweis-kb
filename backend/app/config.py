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
    APP_NAME: str = "企业知识库"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production"] = "development"

    # ── Database ───────────────────────────────────────
    DB_USER: str = "kb_user"
    DB_PASSWORD: str = "change-me"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "kb_database"

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
    OPS_AGENT_KEY: str = ""

    # ── MinIO ──────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ONLYOFFICE_ENDPOINT: str = ""  # OnlyOffice container reachable MinIO endpoint (empty = public)
    MINIO_ONLYOFFICE_SECURE: bool = False
    MINIO_PUBLIC_ENDPOINT: str = ""  # 公网访问地址，留空则等于 MINIO_ENDPOINT
    MINIO_PUBLIC_SECURE: bool = False  # 公网预签名 URL 是否走 HTTPS（内部 MINIO_SECURE 单独控制）
    MINIO_ACCESS_KEY: str = "change-me"
    MINIO_SECRET_KEY: str = "change-me"
    MINIO_BUCKET: str = "kb-documents"
    MINIO_SECURE: bool = False
    MINIO_PRESIGNED_EXPIRES: int = 3600  # 预签名 URL 有效期(秒)

    # ── Gotenberg ──────────────────────────────────────
    GOTENBERG_URL: str = "http://localhost:3000"

    # ── OnlyOffice Document Server ─────────────────────
    ONLYOFFICE_URL: str = ""  # 对外可达的 Document Server 地址（如 https://office.example.com/onlyoffice）
    ONLYOFFICE_INTERNAL_BASE: str = "http://172.17.0.1:8000"  # OnlyOffice 容器可达的后端取件地址
    ONLYOFFICE_JWT_SECRET: str = ""  # 与 Document Server JWT_SECRET 保持一致

    # ── AI access ──────────────────────────────────────
    AI_API_KEY: str = ""  # AI 系统调用 /api/ai/* 时使用的 X-AI-Key
    AI_RATE_LIMIT: int = 60  # 每个数字员工密钥每分钟最大请求数
    EMBEDDING_URL: str = ""  # 语义检索用的向量服务地址（OpenAI 兼容 /embed）
    EMBEDDING_MODEL: str = ""  # 向量模型名（OpenAI 兼容 /embeddings 的 model 参数）
    OCR_API_URL: str = ""  # 本地 PaddleOCR 文档解析服务（文档解析工作台）
    OCR_API_KEY: str = ""  # PaddleOCR API 密钥（x-api-key）

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
        extra = "ignore"  # Ignore old-style keys like DATABASE_URL in .env


settings = Settings()

DEPARTMENTS = [
    "总经办",
    "人力资源部",
    "财务部",
    "市场部",
    "注册部",
    "医学部部",
    "临床运营部",
    "临床研究部",
    "质量部",
    "商务部",
    "国际部",
    "公共共享区",
]

ROLES = [
    "super_admin",
    "dept_admin",
    "editor",
    "employee",
    "guest",
]
