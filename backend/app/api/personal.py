from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.favorite import Favorite, BrowseHistory
from app.schemas import DocumentItem, PersonalStats
from app.api.documents import _doc_to_item
import uuid as _uuid

router = APIRouter()


@router.get("/uploads")
async def my_uploads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Document)
        .where(Document.uploader_id == current_user.id, Document.is_deleted == False)
        .order_by(Document.created_at.desc())
    )
    count_query = (
        select(func.count(Document.id))
        .where(Document.uploader_id == current_user.id, Document.is_deleted == False)
    )
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    items = [await _doc_to_item(doc, db) for doc in docs]
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/favorites")
async def my_favorites(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Document)
        .join(Favorite, Favorite.document_id == Document.id)
        .where(Favorite.user_id == current_user.id, Document.is_deleted == False)
        .order_by(Favorite.created_at.desc())
    )
    count_query = (
        select(func.count(Document.id))
        .join(Favorite, Favorite.document_id == Document.id)
        .where(Favorite.user_id == current_user.id, Document.is_deleted == False)
    )
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    items = [await _doc_to_item(doc, db) for doc in docs]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/favorites/{document_id}")
async def add_favorite(
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


@router.get("/history")
async def my_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Document)
        .join(BrowseHistory, BrowseHistory.document_id == Document.id)
        .where(BrowseHistory.user_id == current_user.id, Document.is_deleted == False)
        .order_by(BrowseHistory.created_at.desc())
    )
    count_query = (
        select(func.count(Document.id))
        .join(BrowseHistory, BrowseHistory.document_id == Document.id)
        .where(BrowseHistory.user_id == current_user.id, Document.is_deleted == False)
    )
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    items = [await _doc_to_item(doc, db) for doc in docs]
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/stats")
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
