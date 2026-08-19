from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Model
from app.models.base import Base, TimestampMixin
import uuid as _uuid


class AiApiKey(Model, Base, TimestampMixin):
    __tablename__ = "ai_api_keys"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="all", nullable=False)  # all | dept
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiApiLog(Model, Base):
    __tablename__ = "ai_api_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_id: Mapped[_uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(200), default="")
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
