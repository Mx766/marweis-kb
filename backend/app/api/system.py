from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import require_role
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.system_config import SystemConfig
from app.services.search_service import _get_search_client_sync

router = APIRouter()


@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Return all system settings as a flat key-value dict."""
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
        index_stats = client.index("documents").stats()
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
