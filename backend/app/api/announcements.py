"""更新公告：登录用户读取，超管发布/管理。"""
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models.user import User

router = APIRouter()


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_active: bool = True


@router.get("")
async def list_announcements(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取更新公告（默认仅生效中；超管可带 include_inactive=1 查看全部）。"""
    cond = ""
    if not (include_inactive and current_user.role == "super_admin"):
        cond = "WHERE is_active = true"
    rows = (await db.execute(
        text(
            "SELECT id, title, content, is_active, created_at FROM update_announcements "
            + cond + " ORDER BY created_at DESC LIMIT 100"
        )
    )).all()
    return {"items": [
        {
            "id": str(r[0]), "title": r[1], "content": r[2],
            "is_active": bool(r[3]),
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]}


@router.post("")
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    title = (body.title or "").strip()
    content = (body.content or "").strip()
    if not title or not content:
        raise HTTPException(400, "标题和内容不能为空")
    aid = _uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO update_announcements (id, title, content, is_active, created_at) "
            "VALUES (:id, :title, :content, :active, now())"
        ),
        {"id": aid, "title": title[:200], "content": content[:8000], "active": body.is_active},
    )
    await db.commit()
    return {"id": str(aid), "title": title}


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    await db.execute(
        text(
            "UPDATE update_announcements SET title = :title, content = :content, "
            "is_active = :active WHERE id = :id"
        ),
        {
            "id": _uuid.UUID(announcement_id),
            "title": (body.title or "").strip()[:200],
            "content": (body.content or "").strip()[:8000],
            "active": body.is_active,
        },
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    await db.execute(
        text("DELETE FROM update_announcements WHERE id = :id"),
        {"id": _uuid.UUID(announcement_id)},
    )
    await db.commit()
    return {"ok": True}
