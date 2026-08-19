from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_optional, require_role
from app.permissions import PermissionService
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.system_config import SystemConfig
from app.services.search_service import _get_search_client_sync

router = APIRouter()


@router.get("/stats")
async def homepage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """首页统计：按当前用户可见分类过滤（部门管理员只看本部门+公共分类）。"""
    from sqlalchemy import false as sa_false

    perm = PermissionService(db, current_user)
    visible_ids = await perm.get_visible_category_ids()

    conditions = [Document.is_deleted == False]
    if current_user and current_user.role == "super_admin":
        pass  # 超管看全系统
    elif visible_ids:
        # 与文档列表接口一致：未分类文档（category_id IS NULL）不进入普通用户统计
        conditions.append(Document.category_id.in_(visible_ids))
    else:
        conditions.append(sa_false())

    total_docs = (await db.execute(
        select(func.count(Document.id)).where(*conditions)
    )).scalar() or 0

    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    week_updates = (await db.execute(
        select(func.count(Document.id)).where(*conditions, Document.updated_at >= week_ago)
    )).scalar() or 0

    if current_user and current_user.role == "super_admin":
        total_categories = (await db.execute(
            select(func.count(Category.id))
        )).scalar() or 0
    else:
        total_categories = (await db.execute(
            select(func.count(Category.id)).where(Category.id.in_(visible_ids))
        )).scalar() or 0 if visible_ids else 0

    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0

    return {
        "total_docs": total_docs,
        "week_updates": week_updates,
        "total_categories": total_categories,
        "active_users": active_users,
    }


@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
):
    """Return all system settings as a flat key-value dict（公开，供主题/品牌展示）。"""
    result = await db.execute(select(SystemConfig))
    configs = {row.key: row.value for row in result.scalars().all()}
    return configs


@router.put("/settings")
async def update_settings(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Upsert system settings. Only super_admin can modify."""
    for key, value in body.items():
        key_str = str(key)[:100]
        val_str = str(value) if value is not None else ""
        existing = await db.get(SystemConfig, key_str)
        if existing:
            existing.value = val_str
        else:
            db.add(SystemConfig(key=key_str, value=val_str))
    await db.commit()
    return {"message": "设置已保存"}


@router.get("/search-stats")
async def search_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Return Meilisearch vs PostgreSQL sync status."""
    try:
        client = _get_search_client_sync()
        idx = client.index("documents")
        index_stats = idx.get_stats() if hasattr(idx, "get_stats") else idx.stats()
        if hasattr(index_stats, "number_of_documents"):
            meili_count = index_stats.number_of_documents
        else:
            meili_count = index_stats.get("numberOfDocuments", 0)
    except Exception:
        meili_count = 0

    # PostgreSQL non-deleted document count
    result = await db.execute(
        select(func.count(Document.id)).where(Document.is_deleted == False)
    )
    pg_count = result.scalar() or 0

    # User and category counts
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    cat_count = (await db.execute(select(func.count(Category.id)))).scalar() or 0

    return {
        "meilisearch_docs": meili_count,
        "postgresql_docs": pg_count,
        "unsynced": pg_count - meili_count if pg_count else 0,
        "health": "healthy" if abs(pg_count - meili_count) < 10 else "drifted",
        "total_users": user_count,
        "total_categories": cat_count,
    }
