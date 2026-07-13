from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.schemas import SearchResult
from app.permissions import PermissionService
from app.services.search_service import search_documents
from app.api.documents import _doc_to_item
import uuid as _uuid

router = APIRouter()


@router.get("")
async def search(
    q: str = Query("", min_length=0),
    category_id: str = Query(None),
    file_type: str = Query(None),
    tag: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # Get visible category IDs for permission filtering
    allowed_cat_ids: list[str] | None = None
    if current_user is None:
        cats = await db.execute(select(Category))
        allowed_cat_ids = [str(c.id) for c in cats.scalars().all() if c.visible_departments is None]
    elif current_user.role != "super_admin":
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        allowed_cat_ids = [str(v) for v in visible]

    # Try Meilisearch first, fall back to SQL LIKE
    result = search_documents(
        query=q,
        page=page,
        size=size,
        category_id=category_id,
        file_type=file_type,
        allowed_category_ids=allowed_cat_ids,
    )

    if result["hits"]:
        # Map Meilisearch results to DocumentItem
        items = []
        for hit in result["hits"]:
            doc_id = hit["id"]
            doc = await db.get(Document, _uuid.UUID(doc_id))
            if doc and not doc.is_deleted:
                items.append(await _doc_to_item(doc, db))
        return SearchResult(
            items=items,
            total=result["total"],
            query=q,
            page=page,
            size=size,
        )

    # Fallback: SQL LIKE search
    conditions = [Document.is_deleted == False]
    if q.strip():
        conditions.append(
            (Document.title.ilike(f"%{q}%")) | (Document.summary.ilike(f"%{q}%"))
        )
    if category_id:
        conditions.append(Document.category_id == _uuid.UUID(category_id))
    if file_type:
        conditions.append(Document.file_type == file_type)
    if tag:
        from sqlalchemy import cast, String
        # Search for tag in JSON array by string-matching the tags column
        conditions.append(
            cast(Document.tags, String).ilike(f"%{tag}%")
        )
    if allowed_cat_ids:
        conditions.append(Document.category_id.in_([_uuid.UUID(c) for c in allowed_cat_ids]))

    query_obj = select(Document).where(*conditions).order_by(Document.updated_at.desc())
    count_query = select(func.count(Document.id)).where(*conditions)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query_obj.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    items = [await _doc_to_item(doc, db) for doc in docs]
    return SearchResult(
        items=items,
        total=total,
        query=q,
        page=page,
        size=size,
    )
