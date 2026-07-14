from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, get_current_user_optional, require_role
from app.models.user import User
from app.models.category import Category
from app.models.document import Document
from app.schemas import CategoryNode, CategoryCreate, CategoryUpdate
from app.permissions import PermissionService, get_permission_service
import uuid as _uuid

router = APIRouter()


def _build_tree(categories: list[Category], parent_id: _uuid.UUID | None = None) -> list[CategoryNode]:
    nodes = []
    children = [c for c in categories if c.parent_id == parent_id]
    children.sort(key=lambda c: c.sort_order)
    for cat in children:
        node = CategoryNode(
            id=str(cat.id),
            name=cat.name,
            parent_id=str(cat.parent_id) if cat.parent_id else None,
            sort_order=cat.sort_order,
            icon=cat.icon,
            visible_departments=cat.visible_departments,
            description=cat.description,
            children=_build_tree(categories, cat.id),
        )
        nodes.append(node)
    return nodes


@router.get("")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is None:
        # Guest: show only public categories (SQL-level filter)
        result = await db.execute(
            select(Category)
            .where(Category.visible_departments.is_(None))
            .order_by(Category.sort_order)
        )
        return _build_tree(result.scalars().all())

    if current_user.role == "super_admin":
        result = await db.execute(select(Category).order_by(Category.sort_order))
        return _build_tree(result.scalars().all())

    # Non-admin: load all, filter in Python (only ~40 rows, fine for this scale)
    result = await db.execute(select(Category).order_by(Category.sort_order))
    all_cats = result.scalars().all()
    visible = [
        c for c in all_cats
        if c.visible_departments is None
        or current_user.department in (c.visible_departments or [])
        or "*" in (c.visible_departments or [])
    ]
    return _build_tree(visible)


@router.post("")
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    cat = Category(
        name=body.name,
        parent_id=_uuid.UUID(body.parent_id) if body.parent_id else None,
        sort_order=body.sort_order,
        icon=body.icon,
        visible_departments=body.visible_departments,
        description=body.description,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    await db.commit()
    return {"id": str(cat.id), "name": cat.name}


@router.put("/{category_id}")
async def update_category(
    category_id: str,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    cat = await db.get(Category, _uuid.UUID(category_id))
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    update_data = body.model_dump(exclude_unset=True)

    # Prevent cycles: new parent_id must not be a descendant of this category
    new_parent_id = update_data.get("parent_id")
    if new_parent_id and _uuid.UUID(new_parent_id) != _uuid.UUID(category_id):
        # Walk up from the proposed parent to check it doesn't descend from cat
        current = await db.get(Category, _uuid.UUID(new_parent_id))
        while current and current.parent_id:
            if current.parent_id == cat.id:
                raise HTTPException(status_code=400, detail="不能将分类移动到其子分类下（会造成循环）")
            current = await db.get(Category, current.parent_id)

    for key, val in update_data.items():
        setattr(cat, key, val)
    await db.flush()
    await db.commit()
    return {"id": str(cat.id), "name": cat.name}


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    cat = await db.get(Category, _uuid.UUID(category_id))
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    # Reassign child categories to the deleted category's parent
    child_cats = (await db.execute(
        select(Category).where(Category.parent_id == cat.id)
    )).scalars().all()
    for child in child_cats:
        child.parent_id = cat.parent_id

    # Orphan documents in this category: set category_id to NULL
    orphan_docs = (await db.execute(
        select(Document).where(Document.category_id == cat.id)
    )).scalars().all()
    for doc in orphan_docs:
        doc.category_id = None

    await db.delete(cat)
    await db.commit()
    return {"message": "分类已删除"}
