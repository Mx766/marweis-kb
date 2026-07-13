from sqlalchemy import String, Integer, JSON
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
