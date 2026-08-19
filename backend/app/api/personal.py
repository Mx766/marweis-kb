from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.favorite import Favorite, BrowseHistory
from app.schemas import DocumentItem, PersonalStats, DocumentListResponse
from app.api.documents import _doc_to_item, _batch_load_uploaders
from app.permissions import PermissionService
import uuid as _uuid

router = APIRouter()


@router.get("/uploads", response_model=DocumentListResponse)
async def my_uploads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_cond = [Document.uploader_id == current_user.id, Document.is_deleted == False]

    query = (
        select(Document)
        .where(*base_cond)
        .order_by(Document.created_at.desc())
    )
    count_query = select(func.count(Document.id)).where(*base_cond)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    uploader_map = await _batch_load_uploaders(db, docs)
    items = [_doc_to_item(doc, uploader_map.get(doc.uploader_id)) for doc in docs]

    return DocumentListResponse(
        items=items, total=total, page=page, size=size,
        pages=max(1, (total + size - 1) // size),
    )


@router.get("/favorites", response_model=DocumentListResponse)
async def my_favorites(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_cond = [Favorite.user_id == current_user.id, Document.is_deleted == False]

    query = (
        select(Document)
        .join(Favorite, Favorite.document_id == Document.id)
        .where(*base_cond)
        .order_by(Favorite.created_at.desc())
    )
    count_query = (
        select(func.count(Document.id))
        .join(Favorite, Favorite.document_id == Document.id)
        .where(*base_cond)
    )

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    uploader_map = await _batch_load_uploaders(db, docs)
    items = [_doc_to_item(doc, uploader_map.get(doc.uploader_id)) for doc in docs]

    return DocumentListResponse(
        items=items, total=total, page=page, size=size,
        pages=max(1, (total + size - 1) // size),
    )


@router.post("/favorites/{document_id}")
async def add_favorite(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify document exists and user can view it
    doc = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权访问该文档")

    existing = (
        await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.document_id == _uuid.UUID(document_id),
            )
        )
    ).scalar_one_or_none()
    if not existing:
        fav = Favorite(user_id=current_user.id, document_id=_uuid.UUID(document_id))
        db.add(fav)
        await db.flush()
        await db.commit()
    return {"message": "已收藏"}


@router.delete("/favorites/{document_id}")
async def remove_favorite(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.document_id == _uuid.UUID(document_id),
            )
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()
        await db.commit()
    return {"message": "已取消收藏"}


@router.get("/history", response_model=DocumentListResponse)
async def my_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_cond = [BrowseHistory.user_id == current_user.id, Document.is_deleted == False]

    query = (
        select(Document)
        .join(BrowseHistory, BrowseHistory.document_id == Document.id)
        .where(*base_cond)
        .order_by(BrowseHistory.created_at.desc())
    )
    count_query = (
        select(func.count(Document.id))
        .join(BrowseHistory, BrowseHistory.document_id == Document.id)
        .where(*base_cond)
    )

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    uploader_map = await _batch_load_uploaders(db, docs)
    items = [_doc_to_item(doc, uploader_map.get(doc.uploader_id)) for doc in docs]

    return DocumentListResponse(
        items=items, total=total, page=page, size=size,
        pages=max(1, (total + size - 1) // size),
    )


@router.get("/stats", response_model=PersonalStats)
async def personal_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uploads = (await db.execute(
        select(func.count(Document.id)).where(
            Document.uploader_id == current_user.id, Document.is_deleted == False
        )
    )).scalar()
    favorites = (await db.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == current_user.id)
    )).scalar()
    history = (await db.execute(
        select(func.count(BrowseHistory.id)).where(BrowseHistory.user_id == current_user.id)
    )).scalar()
    return PersonalStats(total_uploads=uploads or 0, total_favorites=favorites or 0, total_history=history or 0)
