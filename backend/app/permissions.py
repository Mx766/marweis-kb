from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.document import Document
import uuid as _uuid

from app.auth import get_current_user, get_current_user_optional


class PermissionService:
    def __init__(self, db: AsyncSession, current_user: User | None):
        self.db = db
        self.user = current_user

    async def get_visible_category_ids(self) -> list[_uuid.UUID]:
        """Return category IDs visible to the current user — filtered at DB level."""
        if self.user is None:
            # Guest: only public categories (visible_departments is None)
            result = await self.db.execute(
                select(Category.id).where(Category.visible_departments.is_(None))
            )
            return [row[0] for row in result.all()]

        if self.user.role == "super_admin":
            result = await self.db.execute(select(Category.id))
            return [row[0] for row in result.all()]

        # Load all categories, filter in Python (small table, avoids JSON operator issues)
        result = await self.db.execute(select(Category))
        all_cats = result.scalars().all()
        return [
            c.id for c in all_cats
            if c.visible_departments is None
            or self.user.department in (c.visible_departments or [])
            or "*" in (c.visible_departments or [])
        ]

    async def can_view_document(self, doc: Document) -> bool:
        # Unclassified documents (category_id IS NULL) are treated as draft/private:
        # only super_admin and the uploader can view them.
        # This prevents accidental exposure of sensitive documents that
        # haven't been properly categorized yet.
        if doc.category_id is None:
            if self.user is None:
                return False
            return self.user.role == "super_admin" or doc.uploader_id == self.user.id

        if self.user is None:
            # Guest: only documents in public categories
            result = await self.db.execute(
                select(Category.id).where(
                    Category.id == doc.category_id,
                    Category.visible_departments.is_(None),
                )
            )
            return result.scalar_one_or_none() is not None

        if self.user.role == "super_admin":
            return True
        if doc.uploader_id == self.user.id:
            return True

        visible_ids = await self.get_visible_category_ids()
        return doc.category_id in visible_ids

    async def can_edit_document(self, doc: Document) -> bool:
        if self.user.role == "super_admin":
            return True
        if self.user.role == "dept_admin":
            return await self.can_view_document(doc)
        if self.user.role == "editor" and doc.uploader_id == self.user.id:
            return True
        return False

    async def can_delete_document(self, doc: Document) -> bool:
        return await self.can_edit_document(doc)


async def get_permission_service(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> AsyncGenerator[PermissionService, None]:
    """Dependency that injects PermissionService — supports guest users (None)."""
    yield PermissionService(db, current_user)
