from sqlalchemy import String, Integer, BigInteger, Boolean, Date, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Model
from app.models.base import Base, TimestampMixin
import uuid as _uuid
import datetime


class Document(Model, Base, TimestampMixin):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[_uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "file" | "link"
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    preview_path: Mapped[str | None] = mapped_column(String(1000))
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_ext: Mapped[str] = mapped_column(String(20), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    effective_date: Mapped[datetime.date | None] = mapped_column(Date)
    version: Mapped[str | None] = mapped_column(String(50))
    uploader_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
