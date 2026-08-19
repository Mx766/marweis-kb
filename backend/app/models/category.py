from sqlalchemy import String, Integer, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Model
from app.models.base import Base, TimestampMixin
import uuid as _uuid


class Category(Model, Base, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[_uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str | None] = mapped_column(String(50))
    visible_departments: Mapped[list[str] | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(500))
    allow_upload: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # 权限模式: admin_only=仅部门负责人可见/可传; member_download=全员可见、负责人上传、员工可下载;
    # member_upload=全员可见自己的、员工可上传不可下载; view_only=全员可见、员工仅可看;
    # NULL=默认行为(全员可见, 是否可上传看 allow_upload, 员工可下载)
    permission_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
