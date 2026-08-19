from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Model
from app.models.base import Base, TimestampMixin
import uuid as _uuid


class UserFile(Model, Base, TimestampMixin):
    __tablename__ = "user_files"

    user_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_ext: Mapped[str] = mapped_column(String(20), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    department: Mapped[str] = mapped_column(String(100), default="")
    # 公盘/私盘: dept=部门公盘, private=员工个人私盘
    scope: Mapped[str] = mapped_column(String(20), default="dept", index=True)
    # 可见范围（scope=all 全员；scope=specific 时列出可见部门名）
    visible_departments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 指定人员可见（scope=users 时列出可见用户 id）
    visible_user_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 仅管理员可见（True 时普通员工不可见，部门管理员/超管可见）
    admin_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    # 是否开放给员工下载（False 时非管理员仅可在线预览/不可下载）
    employee_download: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[_uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    in_trash: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
