"""AI-only endpoints for digital employees / agents.

Exposes machine-readable Markdown copies of documents with per-key auth,
department isolation, search, and bulk export. Keys are managed by super
admins in the admin UI (or these endpoints).
"""
import hashlib
import io
import json
import logging
import secrets
import time
import zipfile
from collections import defaultdict, deque
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.config import settings
from app.database import get_db, async_session_maker
from app.models.ai_key import AiApiKey, AiApiLog
from app.models.category import Category
from app.models.document import Document
from app.models.user import User
from app.services.markdown_service import queue_markdown_generation
from app.services.search_service import ai_search_documents

logger = logging.getLogger(__name__)
router = APIRouter()

_RATE_WINDOW = 60
_RATE_LIMIT = int(getattr(settings, "AI_RATE_LIMIT", 60) or 60)
_RATE: dict[str, deque] = defaultdict(deque)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _new_key() -> str:
    return "mw_" + secrets.token_urlsafe(28)


async def _visible_category_ids(db: AsyncSession, department: str) -> list:
    result = await db.execute(select(Category.id, Category.visible_departments))
    return [
        cid
        for cid, deps in result.all()
        if deps is None or department in deps or "*" in deps
    ]


async def _scope_conditions(db: AsyncSession, key: AiApiKey | None) -> list:
    if key is None or key.scope != "dept" or not key.department:
        return []
    visible = await _visible_category_ids(db, key.department)
    if not visible:
        return [text("1 = 0")]
    return [Document.category_id.in_(visible)]


async def _log_ai_call(key: AiApiKey | None, endpoint: str, ip: str | None) -> None:
    try:
        async with async_session_maker() as db:
            db.add(AiApiLog(key_id=key.id if key else None, endpoint=endpoint[:200], ip=ip))
            await db.commit()
    except Exception:
        logger.warning("Failed to write AI audit log", exc_info=True)


async def _require_ai_access(
    request: Request,
    x_ai_key: str | None = Header(default=None, alias="X-AI-Key"),
    db: AsyncSession = Depends(get_db),
) -> None:
    key: AiApiKey | None = None
    if x_ai_key:
        key = (
            await db.execute(
                select(AiApiKey).where(
                    AiApiKey.key_hash == _hash_key(x_ai_key),
                    AiApiKey.active == True,
                )
            )
        ).scalar_one_or_none()
        if not key:
            raise HTTPException(status_code=401, detail="无效的 AI 访问凭证")
        request.state.ai_key = key
        # rate limit per key
        now = time.time()
        bucket = _RATE[key.id]
        while bucket and now - bucket[0] > _RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        bucket.append(now)
        key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth[7:])
                user = await db.get(User, payload.get("sub"))
                if user and user.is_active and user.role == "super_admin":
                    request.state.ai_key = None
                    key = None
                else:
                    raise HTTPException(status_code=401, detail="无效的 AI 访问凭证")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=401, detail="无效的 AI 访问凭证")
        else:
            raise HTTPException(status_code=401, detail="缺少 X-AI-Key 或管理员凭证")
    await _log_ai_call(key, request.url.path, request.client.host if request.client else None)


async def _require_super_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="需要管理员登录")
    try:
        payload = decode_token(auth[7:])
        user = await db.get(User, payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="无效凭证")
    if not user or not user.is_active or user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可操作")
    return user


def _serialize(doc: Document, include_content: bool, category_name: str | None = None) -> dict:
    data = {
        "id": str(doc.id),
        "title": doc.title,
        "category_id": str(doc.category_id) if doc.category_id else None,
        "category_name": category_name,
        "file_type": doc.file_type,
        "file_ext": doc.file_ext,
        "file_size": doc.file_size,
        "markdown_status": doc.markdown_status,
        "markdown_path": doc.markdown_path,
        "markdown_updated_at": (
            doc.markdown_updated_at.isoformat() if doc.markdown_updated_at else None
        ),
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
    if include_content:
        data["markdown_content"] = doc.markdown_content
    return data


async def _load_categories(db: AsyncSession, docs: list[Document]) -> dict:
    cat_ids = {doc.category_id for doc in docs if doc.category_id}
    cat_map: dict = {}
    if cat_ids:
        result = await db.execute(select(Category.id, Category.name).where(Category.id.in_(cat_ids)))
        cat_map = {row[0]: row[1] for row in result.all()}
    return cat_map


@router.get("/ping")
async def ai_ping(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    key: AiApiKey | None = getattr(request.state, "ai_key", None)
    return {
        "ok": True,
        "auth": "key" if key else "super_admin",
        "name": key.name if key else None,
        "scope": key.scope if key else "all",
        "department": key.department if key else None,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/documents")
async def list_ai_documents(
    request: Request,
    status: str = Query("done", pattern="^(done|pending|failed|unsupported|any)$"),
    category_id: str | None = Query(None),
    file_ext: str | None = Query(None),
    q: str | None = Query(None),
    updated_after: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_content: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    key: AiApiKey | None = getattr(request.state, "ai_key", None)
    conditions = [Document.is_deleted == False, *await _scope_conditions(db, key)]
    if status != "any":
        conditions.append(Document.markdown_status == status)
    if category_id:
        conditions.append(Document.category_id == category_id)
    if file_ext:
        conditions.append(Document.file_ext == file_ext.lower())
    if q:
        conditions.append(Document.title.ilike(f"%{q}%"))
    if updated_after:
        conditions.append(Document.updated_at >= updated_after)

    total = (await db.execute(select(func.count(Document.id)).where(*conditions))).scalar_one()
    result = await db.execute(
        select(Document).where(*conditions).order_by(Document.updated_at.desc()).offset(offset).limit(limit)
    )
    docs = result.scalars().all()
    cat_map = await _load_categories(db, docs)
    return {
        "items": [_serialize(doc, include_content, cat_map.get(doc.category_id)) for doc in docs],
        "offset": offset,
        "limit": limit,
        "count": len(docs),
        "total": total,
    }


@router.get("/search")
async def ai_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50),
    category_id: str | None = Query(None),
    semantic: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    key: AiApiKey | None = getattr(request.state, "ai_key", None)
    conditions = [
        "d.is_deleted = false AND d.markdown_status = 'done'",
        "length(d.markdown_content) >= 100",
    ]
    if category_id:
        conditions.append("d.category_id = :category_id")
    if key and key.scope == "dept" and key.department:
        visible = await _visible_category_ids(db, key.department)
        if not visible:
            return {"items": [], "query": q, "semantic": semantic}
        conditions.append("d.category_id = ANY(:visible)")

    if semantic:
        if not settings.EMBEDDING_URL:
            raise HTTPException(status_code=503, detail="语义检索未配置（EMBEDDING_URL）")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload: dict = {"input": [q]}
                if settings.EMBEDDING_MODEL:
                    payload["model"] = settings.EMBEDDING_MODEL
                resp = await client.post(
                    f"{settings.EMBEDDING_URL.rstrip('/')}/embeddings",
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
                if isinstance(body, dict) and body.get("data"):
                    vector = body["data"][0]["embedding"]
                elif isinstance(body, list):
                    vector = body[0]["embedding"]
                else:
                    vector = body["embeddings"][0]
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"向量服务不可用: {exc}")
        vec_str = "[" + ",".join(str(x) for x in vector) + "]"
        where = " AND ".join(conditions)
        sql = (
            "SELECT d.id, d.title, d.category_id, d.file_ext, d.markdown_status, d.updated_at, "
            "(d.embedding <=> CAST(:vec AS vector)) AS dist "
            f"FROM documents d WHERE {where} ORDER BY dist ASC LIMIT :limit"
        )
        params: dict = {"vec": vec_str, "limit": limit}
        if category_id:
            params["category_id"] = category_id
        if key and key.scope == "dept" and key.department:
            params["visible"] = visible
        result = await db.execute(text(sql), params)
        rows = result.all()
        items = []
        for row in rows:
            doc = await db.get(Document, row[0])
            if doc:
                items.append(_serialize(doc, include_content=True))
        return {"items": items, "query": q, "semantic": True}

    # Keyword search via Meilisearch (CJK-aware), with SQL fallback.
    visible_ids = None
    if key and key.scope == "dept" and key.department:
        visible_ids = [str(x) for x in await _visible_category_ids(db, key.department)]
        if not visible_ids:
            return {"items": [], "query": q, "semantic": False}
    hits = await ai_search_documents(q, min(limit * 5, 50), visible_ids)
    if hits:
        import uuid as _uuid
        doc_ids = []
        for h in hits:
            try:
                doc_ids.append(_uuid.UUID(h["id"]))
            except Exception:
                continue
        docs = []
        for i in range(0, len(doc_ids), 100):
            chunk = doc_ids[i : i + 100]
            docs.extend(
                (
                    await db.execute(select(Document).where(Document.id.in_(chunk)))
                ).scalars().all()
            )
        doc_map = {doc.id: doc for doc in docs}
        cat_map = await _load_categories(db, docs)
        items = []
        seen = set()
        for hit in hits:
            doc = doc_map.get(_uuid.UUID(hit["id"])) if "id" in hit else None
            if not doc or not doc.markdown_content or len(doc.markdown_content) < 100:
                continue
            dedupe_key = hashlib.md5(doc.markdown_content[:5000].encode("utf-8")).hexdigest()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            formatted = hit.get("_formatted") or {}
            snippet = (
                formatted.get("markdown_content")
                or formatted.get("title")
                or (doc.markdown_content or "")[:200]
            )
            snippet = str(snippet).replace("[[", "").replace("]]", "").replace("\n", " ")
            item = _serialize(doc, include_content=False, category_name=cat_map.get(doc.category_id))
            item["snippet"] = snippet[:300]
            items.append(item)
        return {"items": items[:limit], "query": q, "semantic": False}

    # Fallback: SQL trigram search (best-effort).
    pattern = f"%{q}%"
    where = " AND ".join(conditions)
    sql = (
        "SELECT d.id, d.title, d.category_id, d.file_ext, d.markdown_status, d.updated_at, "
        "(CASE WHEN d.title ILIKE :p THEN 8 ELSE 0 END"
        " + GREATEST(similarity(d.markdown_content, :q), similarity(d.title, :q)) * 10) AS score "
        f"FROM documents d WHERE {where} AND (d.title ILIKE :p OR similarity(d.markdown_content, :q) > 0.12) "
        "ORDER BY score DESC, d.updated_at DESC LIMIT :limit"
    )
    params: dict = {"p": pattern, "q": q, "limit": limit}
    if category_id:
        params["category_id"] = category_id
    if visible_ids is not None:
        params["visible"] = visible_ids
    result = await db.execute(text(sql), params)
    rows = result.all()
    docs = []
    for row in rows:
        doc = await db.get(Document, row[0])
        if doc:
            docs.append(doc)
    cat_map = await _load_categories(db, docs)
    items = []
    for doc in docs:
        md = doc.markdown_content or ""
        idx = md.lower().find(q.lower())
        snippet = (md[max(0, idx - 80) : idx + 200] if idx >= 0 else md[:200]).replace("\n", " ")
        item = _serialize(doc, include_content=False, category_name=cat_map.get(doc.category_id))
        item["snippet"] = snippet
        items.append(item)
    return {"items": items, "query": q, "semantic": False}


@router.get("/export")
async def ai_export(
    request: Request,
    format: str = Query("zip", pattern="^(zip|jsonl)$"),
    updated_after: datetime | None = Query(None),
    category_id: str | None = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    key: AiApiKey | None = getattr(request.state, "ai_key", None)
    conditions = [
        Document.is_deleted == False,
        Document.markdown_status == "done",
        Document.markdown_content.isnot(None),
        *await _scope_conditions(db, key),
    ]
    if updated_after:
        conditions.append(Document.updated_at >= updated_after)
    if category_id:
        conditions.append(Document.category_id == category_id)
    result = await db.execute(
        select(Document).where(*conditions).order_by(Document.updated_at).limit(limit)
    )
    docs = result.scalars().all()
    cat_map = await _load_categories(db, docs)

    if format == "jsonl":
        def gen():
            for doc in docs:
                item = _serialize(doc, include_content=True, category_name=cat_map.get(doc.category_id))
                yield json.dumps(item, ensure_ascii=False) + "\n"

        return StreamingResponse(
            gen(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=ai_kb_export.jsonl"},
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        index = []
        for doc in docs:
            name = f"{doc.id}.md"
            zf.writestr(name, doc.markdown_content or "")
            index.append(_serialize(doc, include_content=False, category_name=cat_map.get(doc.category_id)))
        zf.writestr("index.json", json.dumps(index, ensure_ascii=False, indent=1))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ai_kb_export.zip"},
    )


@router.get("/documents/{document_id}/markdown")
async def get_document_markdown(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    import uuid as _uuid
    try:
        doc_uuid = _uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="文档不存在")
    key: AiApiKey | None = getattr(request.state, "ai_key", None)
    doc = await db.get(Document, doc_uuid)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    if key and key.scope == "dept" and key.department:
        visible = await _visible_category_ids(db, key.department)
        if not doc.category_id or doc.category_id not in visible:
            raise HTTPException(status_code=404, detail="文档不存在")
    if doc.markdown_status != "done" or not doc.markdown_content:
        raise HTTPException(status_code=404, detail="该文档暂无 Markdown 内容")
    category_name = None
    if doc.category_id:
        cat = await db.get(Category, doc.category_id)
        category_name = cat.name if cat else None
    return _serialize(doc, include_content=True, category_name=category_name)


@router.post("/documents/{document_id}/markdown/refresh")
async def refresh_document_markdown(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_ai_access),
):
    import uuid as _uuid
    try:
        doc_uuid = _uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc = await db.get(Document, doc_uuid)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    queue_markdown_generation(str(doc.id))
    return {"id": document_id, "status": "queued"}


# ── Key management (super admin only) ──────────────────────────


@router.get("/keys")
async def list_ai_keys(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_super_admin),
):
    result = await db.execute(
        select(AiApiKey).order_by(AiApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    count_rows = (
        await db.execute(
            select(AiApiLog.key_id, func.count(AiApiLog.id))
            .where(AiApiLog.key_id.isnot(None))
            .group_by(AiApiLog.key_id)
        )
    ).all()
    counts = {row[0]: row[1] for row in count_rows}
    return {
        "items": [
            {
                "id": str(k.id),
                "name": k.name,
                "scope": k.scope,
                "department": k.department,
                "active": k.active,
                "key_hint": (k.key_prefix + "****") if k.key_prefix else "****",
                "call_count": counts.get(k.id, 0),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]
    }


@router.post("/keys")
async def create_ai_key(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_super_admin),
):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请输入密钥名称")
    scope = body.get("scope") or "all"
    if scope not in ("all", "dept"):
        raise HTTPException(status_code=400, detail="scope 只能是 all 或 dept")
    department = (body.get("department") or "").strip() or None
    if scope == "dept" and not department:
        raise HTTPException(status_code=400, detail="部门范围密钥必须指定部门")
    plain = _new_key()
    record = AiApiKey(
        name=name,
        key_hash=_hash_key(plain),
        key_prefix=plain[:8],
        scope=scope,
        department=department,
        active=True,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "id": str(record.id),
        "name": record.name,
        "scope": record.scope,
        "department": record.department,
        "key": plain,  # 仅本次返回
    }


@router.patch("/keys/{key_id}")
async def update_ai_key(
    key_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_super_admin),
):
    import uuid as _uuid
    record = await db.get(AiApiKey, _uuid.UUID(key_id))
    if not record:
        raise HTTPException(status_code=404, detail="密钥不存在")
    if "active" in body:
        record.active = bool(body["active"])
    if "name" in body and (body.get("name") or "").strip():
        record.name = body["name"].strip()
    await db.commit()
    return {"ok": True}


@router.post("/keys/{key_id}/rotate")
async def rotate_ai_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_super_admin),
):
    import uuid as _uuid
    record = await db.get(AiApiKey, _uuid.UUID(key_id))
    if not record:
        raise HTTPException(status_code=404, detail="密钥不存在")
    plain = _new_key()
    record.key_hash = _hash_key(plain)
    record.key_prefix = plain[:8]
    await db.commit()
    return {"id": str(record.id), "key": plain}


@router.delete("/keys/{key_id}")
async def delete_ai_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_super_admin),
):
    import uuid as _uuid
    record = await db.get(AiApiKey, _uuid.UUID(key_id))
    if not record:
        raise HTTPException(status_code=404, detail="密钥不存在")
    await db.delete(record)
    await db.commit()
    return {"ok": True}
