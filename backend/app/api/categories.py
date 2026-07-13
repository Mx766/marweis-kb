from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, get_current_user_optional, require_role
from app.models.user import User
from app.models.category import Category
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
        # Show only public categories (no visible_departments set)
        result = await db.execute(
            select(Category).order_by(Category.sort_order)
        )
        all_cats = result.scalars().all()
        public_cats = [c for c in all_cats if c.visible_departments is None]
        return _build_tree(public_cats)
    perm = PermissionService(db, current_user)
    visible_ids = await perm.get_visible_category_ids()
    result = await db.execute(select(Category).order_by(Category.sort_order))
    all_cats = result.scalars().all()
    visible_cats = [c for c in all_cats if c.id in visible_ids]
    return _build_tree(visible_cats)


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

    await db.delete(cat)
    await db.commit()
    return {"message": "分类已删除"}
