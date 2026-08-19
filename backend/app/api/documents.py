import json
import logging
import asyncio
import time
import hashlib
import uuid as _uuid
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from sqlalchemy import select, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_maker
from app.auth import get_current_user, get_current_user_optional, require_role, decode_token
from app.config import settings
from app.api.oo_source import make_source_token
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.favorite import BrowseHistory
from app.schemas import DocumentCreate, DocumentUpdate, DocumentItem, DocumentDetail, DocumentListResponse
from app.permissions import PermissionService, get_permission_service
from app.services.file_service import FileService, get_minio_client, _run_in_thread
from app.services.search_service import index_document, remove_document
from app.services.markdown_service import queue_markdown_generation
from datetime import date as date_type

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Pre-computed allowed hosts for link-type document preview ──
_ALLOWED_PREVIEW_HOSTS: set[str] = {
    "nmpa.gov.cn", "www.nmpa.gov.cn",
    "cmde.org.cn", "www.cmde.org.cn",
    "samr.gov.cn", "www.samr.gov.cn",
    "fda.gov", "www.fda.gov",
    "ecfr.gov", "www.ecfr.gov",
    "eur-lex.europa.eu",
    "iso.org", "www.iso.org",
    "example.com", "www.example.com",
}


def _doc_to_item(doc: Document, uploader: User | None) -> DocumentItem:
    """Convert a Document ORM instance to a DocumentItem schema.

    Accepts a pre-loaded uploader to avoid N+1 queries — callers should
    batch-load uploaders before calling this in a loop.
    """
    return DocumentItem(
        id=str(doc.id),
        title=doc.title,
        category_id=str(doc.category_id) if doc.category_id else None,
        file_type=doc.file_type,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        file_ext=doc.file_ext,
        mime_type=doc.mime_type,
        tags=doc.tags or [],
        summary=doc.summary,
        source=doc.source,
        source_url=doc.source_url,
        effective_date=str(doc.effective_date) if doc.effective_date else None,
        version=doc.version,
        uploader_name=uploader.display_name if uploader else "未知",
        view_count=doc.view_count,
        content_text=doc.content_text,
        created_at=str(doc.created_at),
        updated_at=str(doc.updated_at),
    )


async def _batch_load_uploaders(db: AsyncSession, docs: list[Document]) -> dict[_uuid.UUID, User]:
    """Load all uploaders for a list of documents in a single query."""
    uploader_ids = {doc.uploader_id for doc in docs}
    if not uploader_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(uploader_ids)))
    return {user.id: user for user in result.scalars().all()}


# ── Convertible extensions for on-demand preview ─────────────
_CONVERTIBLE_EXTS = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "odp", "ods"}

# Extensions previewed natively by OnlyOffice Document Server.
_ONLYOFFICE_EXTS = {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "txt", "csv", "md"}
_ONLYOFFICE_DOC_TYPE = {
    "doc": "word", "docx": "word", "odt": "word", "txt": "word",
    "xls": "cell", "xlsx": "cell", "ods": "cell", "csv": "cell",
    "ppt": "slide", "pptx": "slide", "odp": "slide",
}

# 正在后台转换的文档（doc_id -> 开始时间），用于预览轮询去重
_CONVERTING: dict[str, float] = {}
# 后台转换任务强引用（避免被 GC 回收导致永远“转换中”）
_CONVERT_TASKS: set[asyncio.Task] = set()
# 转换失败记录（doc_id -> 失败时间），24 小时内不重复尝试，避免卡死文件反复阻塞
_CONVERT_FAILED: dict[str, float] = {}
_CONVERT_FAIL_TTL = 24 * 3600


async def _convert_and_cache_async(doc_id: str) -> None:
    """后台把文档转成 PDF 并缓存；完成后前端轮询即可拿到预览。"""
    global _CONVERT_FAILED
    failed = False
    try:
        async with async_session_maker() as db:
            doc = await db.get(Document, _uuid.UUID(doc_id))
            if not doc or doc.is_deleted:
                failed = True
                return
            if doc.preview_path:
                return
            if not await _convert_and_cache(doc, db):
                failed = True
    except Exception:
        failed = True
        logger.warning("Background conversion failed for doc %s", doc_id, exc_info=True)
    finally:
        _CONVERTING.pop(doc_id, None)
        if failed:
            _CONVERT_FAILED[doc_id] = time.time()
            logger.warning("Preview conversion recorded as failed for doc %s", doc_id)
        if len(_CONVERT_FAILED) > 5000:
            now = time.time()
            _CONVERT_FAILED = {k: v for k, v in _CONVERT_FAILED.items() if now - v < _CONVERT_FAIL_TTL}


# ═══════════════════════════════════════════════════════════════
# Document endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("")
async def list_documents(
    category_id: str | None = Query(None),
    file_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("updated_at", pattern="^(updated_at|created_at|effective_date|title|file_size|view_count|download_count)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    conditions = [Document.is_deleted == False]
    # Exclude attachment files: file-type docs sharing source_url with a link
    # article are shown as related attachments on the article page, not
    # standalone in category listings. Standalone file docs that merely carry a
    # source URL (e.g. NMPA cosmetic PDFs) must remain visible.
    from sqlalchemy import exists
    from sqlalchemy.orm import aliased
    LinkDoc = aliased(Document)
    is_attachment = exists().where(
        LinkDoc.file_type == "link",
        LinkDoc.is_deleted == False,
        LinkDoc.source_url.isnot(None),
        LinkDoc.source_url != "",
        LinkDoc.source_url == Document.source_url,
        LinkDoc.id != Document.id,
    )
    conditions.append(
        (Document.file_type == "link") |
        (Document.source_url.is_(None)) |
        (Document.source_url == "") |
        (~is_attachment)
    )
    if file_type:
        # Prefix match: "doc" → doc/docx, "xls" → xls/xlsx
        conditions.append(Document.file_type.ilike(f"{file_type}%"))
    if category_id:
        # Recursive: include documents from parent + all descendant categories
        try:
            parent_uuid = _uuid.UUID(category_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="无效的分类ID格式")
        cat_result = await db.execute(select(Category.id, Category.parent_id))
        all_cats = {row.id: row.parent_id for row in cat_result.all()}
        descendant_ids = [parent_uuid]
        queue = [parent_uuid]
        while queue:
            cur = queue.pop()
            for cid, pid in all_cats.items():
                if pid == cur and cid not in descendant_ids:
                    descendant_ids.append(cid)
                    queue.append(cid)
        conditions.append(Document.category_id.in_(descendant_ids))

    # Permission-based category filtering
    perm = PermissionService(db, current_user)
    visible_ids = await perm.get_visible_category_ids()

    if current_user and current_user.role == "super_admin":
        pass  # Super admin sees all documents — no extra filter needed
    elif visible_ids:
        # User can see documents in visible categories.
        # Unclassified docs (category_id IS NULL) are NOT included — they are
        # private to super_admin and the uploader only (see permissions.py).
        conditions.append(Document.category_id.in_(visible_ids))
    else:
        # User has no visible categories at all — return empty list
        from sqlalchemy import false as sa_false
        conditions.append(sa_false())

    # 结题项目文件备份类栏目(member_upload)：普通员工只能看到自己上传的文档
    if current_user and current_user.role == "employee":
        mu_ids = (
            await db.execute(
                select(Category.id).where(Category.permission_mode == "member_upload")
            )
        ).scalars().all()
        if mu_ids:
            conditions.append(
                or_(Document.category_id.notin_(mu_ids), Document.uploader_id == current_user.id)
            )

    sort_col = getattr(Document, sort)
    if order == "desc":
        sort_col = sort_col.desc().nullslast() if sort == "effective_date" else sort_col.desc()
    elif sort == "effective_date":
        sort_col = sort_col.asc().nullslast()

    query = select(Document).where(*conditions).order_by(sort_col)
    count_query = select(func.count(Document.id)).where(*conditions)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    # Batch-load all uploaders in a single query (eliminates N+1)
    uploader_map = await _batch_load_uploaders(db, docs)

    items = [_doc_to_item(doc, uploader_map.get(doc.uploader_id)) for doc in docs]

    # 员工在 view_only / member_upload 栏目下不可下载（前端据此隐藏下载按钮）
    if current_user and current_user.role == "employee" and docs:
        cat_ids = {d.category_id for d in docs if d.category_id is not None}
        if cat_ids:
            mode_rows = (
                await db.execute(
                    select(Category.id, Category.permission_mode).where(Category.id.in_(cat_ids))
                )
            ).all()
            mode_map = {row.id: row.permission_mode for row in mode_rows}
            for doc, item in zip(docs, items):
                if mode_map.get(doc.category_id) in ("view_only", "member_upload"):
                    item.downloadable = False

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权访问该文档")

    # 浏览量计数用原生 SQL 自增，避免 ORM onupdate 把 updated_at 刷成点击时间
    await db.execute(
        text("UPDATE documents SET view_count = view_count + 1 WHERE id = :id"),
        {"id": doc.id},
    )

    # Record browse history if logged in
    if current_user:
        existing = (await db.execute(
            select(BrowseHistory).where(
                BrowseHistory.user_id == current_user.id,
                BrowseHistory.document_id == doc.id,
            )
        )).scalar_one_or_none()
        if not existing:
            db.add(BrowseHistory(user_id=current_user.id, document_id=doc.id))

    await db.commit()
    await db.refresh(doc)

    # Load uploader name
    uploader = await db.get(User, doc.uploader_id)
    item = _doc_to_item(doc, uploader)
    if current_user and current_user.role == "employee" and doc.category_id:
        cat = await db.get(Category, doc.category_id)
        if cat and cat.permission_mode in ("view_only", "member_upload"):
            item.downloadable = False

    # Load category name for breadcrumb
    category_name = None
    if doc.category_id:
        cat = await db.get(Category, doc.category_id)
        if cat:
            category_name = cat.name

    # Load related attachments only for article-type (link) docs, not for the attachments themselves
    related_attachments = []
    if doc.source_url and doc.file_type == "link":
        att_docs = await db.execute(
            select(Document).where(
                Document.source_url == doc.source_url,
                Document.id != doc.id,
                Document.file_type != "link",
                Document.is_deleted == False,
            ).order_by(Document.title)
        )
        att_list = att_docs.scalars().all()
        # Batch-load uploaders to avoid N+1 queries
        att_uploader_map = await _batch_load_uploaders(db, att_list)
        for att in att_list:
            related_attachments.append(_doc_to_item(att, att_uploader_map.get(att.uploader_id)))

    return DocumentDetail(
        **item.model_dump(),
        preview_path=doc.preview_path,
        original_path=doc.original_path,
        download_count=doc.download_count,
        markdown_content=doc.markdown_content or doc.content_text or "",
        related_attachments=related_attachments,
        category_name=category_name,
    )


@router.post("")
async def create_document(
    title: str = Form(...),
    category_id: str = Form(None),
    tags: str = Form("[]"),
    summary: str = Form(None),
    source: str = Form(None),
    source_url: str = Form(None),
    effective_date: str = Form(None),
    version: str = Form(None),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file or create a link-based document entry."""
    tag_list = json.loads(tags) if isinstance(tags, str) else (tags or [])

    # 普通员工必须选择分类，且该分类必须标记为“允许上传”
    if current_user.role == "employee" and not category_id:
        raise HTTPException(status_code=403, detail="普通员工上传必须指定可上传的分类")

    # Parse effective_date from form string to date object
    parsed_effective_date = None
    if effective_date:
        try:
            parsed_effective_date = date_type.fromisoformat(effective_date)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="生效日期格式无效，请使用 YYYY-MM-DD 格式")

    # Validate category_id exists if provided
    cat_uuid = _uuid.UUID(category_id) if category_id else None
    if cat_uuid:
        cat = await db.get(Category, cat_uuid)
        if not cat:
            raise HTTPException(status_code=400, detail="指定的分类不存在")
        # Check that the user's department can access the target category
        if current_user.role != "super_admin":
            perm = PermissionService(db, current_user)
            visible_ids = await perm.get_visible_category_ids()
            if cat_uuid not in visible_ids:
                raise HTTPException(status_code=403, detail="无权将文档上传到该分类")
        # 普通员工上传权限：member_upload 栏目或 allow_upload 标记为 True 的栏目
        if current_user.role == "employee":
            perm = PermissionService(db, current_user)
            if not await perm.can_upload_to_category(cat_uuid):
                raise HTTPException(status_code=403, detail="该分类不允许员工上传")

    if file:
        # Enforce upload size limit
        if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)")
        content = await file.read()
        result = await FileService.upload_and_convert(content, file.filename or "unknown", file.content_type or "")

        doc = Document(
            title=title,
            category_id=_uuid.UUID(category_id) if category_id else None,
            file_type="file",
            original_filename=file.filename or "unknown",
            original_path=result["original_path"],
            preview_path=result.get("preview_path"),
            file_size=result["file_size"] or 0,
            file_ext=result["file_ext"],
            mime_type=result["mime_type"],
            tags=tag_list,
            summary=summary,
            source=source,
            source_url=source_url,
            effective_date=parsed_effective_date,
            version=version,
            uploader_id=current_user.id,
        )
    elif source_url:
        doc = Document(
            title=title,
            category_id=_uuid.UUID(category_id) if category_id else None,
            file_type="link",
            original_filename=source_url,
            original_path=source_url,
            file_ext="link",
            mime_type="text/html",
            tags=tag_list,
            summary=summary,
            source=source,
            source_url=source_url,
            effective_date=parsed_effective_date,
            version=version,
            uploader_id=current_user.id,
        )
    else:
        raise HTTPException(status_code=400, detail="请上传文件或填写来源链接")

    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()

    # Sync to Meilisearch (fire-and-forget — failure is logged but doesn't block)
    await index_document(doc)
    # Generate the AI Markdown copy in the background.
    queue_markdown_generation(str(doc.id))

    return {"id": str(doc.id), "title": doc.title}


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    body: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_edit_document(doc):
        raise HTTPException(status_code=403, detail="无权编辑该文档")

    update_data = body.model_dump(exclude_unset=True)

    # Validate category_id exists if being updated
    new_cat_id = update_data.get("category_id")
    if new_cat_id:
        cat = await db.get(Category, _uuid.UUID(new_cat_id))
        if not cat:
            raise HTTPException(status_code=400, detail="指定的分类不存在")
        # Check that the user's department can access the target category
        if current_user.role != "super_admin":
            perm = PermissionService(db, current_user)
            visible_ids = await perm.get_visible_category_ids()
            if _uuid.UUID(new_cat_id) not in visible_ids:
                raise HTTPException(status_code=403, detail="无权将文档移动到该分类")

    for key, val in update_data.items():
        setattr(doc, key, val)
    # Keep the AI Markdown copy in sync with article text.
    if doc.file_type == "link":
        if doc.content_text and doc.content_text.strip():
            doc.markdown_content = doc.content_text
            doc.markdown_status = "done"
        elif doc.markdown_status != "done":
            doc.markdown_status = "pending"
    await db.flush()
    await db.commit()

    # Sync updated doc to Meilisearch
    await index_document(doc)

    return {"id": str(doc.id), "message": "更新成功"}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_delete_document(doc):
        raise HTTPException(status_code=403, detail="无权删除该文档")

    doc.is_deleted = True
    await db.flush()
    await db.commit()

    # Remove from Meilisearch
    await remove_document(str(doc.id))

    return {"message": "文档已删除"}


async def _read_from_minio(s3_path: str) -> bytes | None:
    """Read a file from MinIO and return its content. Returns None on failure."""
    try:
        s3 = get_minio_client()
        bucket_key = s3_path[5:]  # strip "s3://"
        bucket, key = bucket_key.split("/", 1)
        resp = await _run_in_thread(s3.get_object, Bucket=bucket, Key=key)
        return await _run_in_thread(lambda: resp["Body"].read())
    except Exception:
        logger.warning("Failed to read from MinIO: %s", s3_path, exc_info=True)
        return None


async def _convert_and_cache(doc: Document, db: AsyncSession) -> bytes | None:
    """Convert a document to PDF via Gotenberg, cache the result, return the PDF bytes."""
    content = await _read_from_minio(doc.original_path)
    if not content:
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"files": (doc.original_filename, content)}
            resp = await client.post(
                f"{settings.GOTENBERG_URL}/forms/libreoffice/convert",
                files=files,
            )
            if resp.status_code != 200:
                logger.warning("Gotenberg returned %d for doc %s", resp.status_code, doc.id)
                return None

            # Cache the preview in MinIO
            s3 = get_minio_client()
            bucket_key = doc.original_path[5:]
            bucket, _ = bucket_key.split("/", 1)
            preview_key = f"previews/{_uuid.uuid4()}/{doc.original_filename.rsplit('.', 1)[0]}.pdf"
            await _run_in_thread(s3.upload_fileobj, BytesIO(resp.content), bucket, preview_key)

            doc.preview_path = f"s3://{bucket}/{preview_key}"
            await db.flush()
            await db.commit()

            return resp.content
    except Exception:
        logger.warning("On-demand conversion failed for doc %s", doc.id, exc_info=True)
        return None


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: str,
    token: str = Query("", description="JWT token for iframe auth (since iframes don't send headers)"),
    db: AsyncSession = Depends(get_db),
):
    """Stream a PDF preview directly to the browser (proxied from MinIO).

    """
    # Authenticate via preview token (scoped, short-lived) or full JWT
    if token:
        try:
            payload = decode_token(token)
        except HTTPException:
            raise HTTPException(status_code=401, detail="无效的预览令牌")
        # Accept both scoped preview tokens and full JWT tokens
        if payload.get("scope") == "preview":
            # Scoped token: verify it's for THIS document
            if payload.get("doc") != document_id:
                raise HTTPException(status_code=403, detail="预览令牌与文档不匹配")
        current_user = await db.get(User, payload["sub"])
        if not current_user or not current_user.is_active:
            raise HTTPException(status_code=403, detail="用户不存在或已停用")
    else:
        current_user = None

    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

    # NOTE: view_count is already incremented in get_document (detail endpoint).
    # Incrementing here as well would double-count every page view.

    # Link-type documents → redirect to external URL
    if doc.file_type == "link":
        target_url = doc.source_url or doc.original_path
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https", ""):
            raise HTTPException(status_code=400, detail="不支持的重定向协议")
        if parsed.hostname and parsed.hostname not in _ALLOWED_PREVIEW_HOSTS:
            raise HTTPException(status_code=400, detail="不支持的外部链接")
        return RedirectResponse(url=target_url)

    # Determine which file to stream (cached preview, or convert on-demand)
    preview_content: bytes | None = None
    if doc.preview_path:
        # Use cached preview PDF
        preview_content = await _read_from_minio(doc.preview_path)
    elif doc.file_ext == "pdf":
        # PDF files: serve the original directly (no conversion needed)
        preview_content = await _read_from_minio(doc.original_path)
    elif doc.file_ext in _CONVERTIBLE_EXTS:
        # 该文档近期转换失败过 → 直接明确报错，不再反复卡 60 秒
        last_fail = _CONVERT_FAILED.get(str(doc.id), 0)
        if last_fail and time.time() - last_fail < _CONVERT_FAIL_TTL:
            raise HTTPException(status_code=502, detail="该文档暂时无法生成预览，请点击“下载原件”查看")
        # 后台转换（Gotenberg），前端轮询：首次预览不阻塞等待，也不自动下载
        if str(doc.id) not in _CONVERTING:
            _CONVERTING[str(doc.id)] = time.time()
            task = asyncio.create_task(_convert_and_cache_async(str(doc.id)))
            _CONVERT_TASKS.add(task)
            task.add_done_callback(_CONVERT_TASKS.discard)
        return JSONResponse(status_code=202, content={"status": "converting"})

    if preview_content:
        # Sanitize filename to ASCII-safe for Content-Disposition header
        safe_name = doc.title.encode("ascii", errors="ignore").decode("ascii").strip() or "document"
        return StreamingResponse(
            BytesIO(preview_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{safe_name}.pdf"'},
        )

    # 预览失败时明确报错，不再自动跳转下载（避免 iframe 意外触发下载）
    raise HTTPException(status_code=502, detail="预览生成失败，请稍后重试或点击“下载原件”")


@router.get("/{document_id}/preview-token")
async def get_preview_token(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a short-lived, single-document preview token for iframe auth.

    Avoids exposing the full JWT in the URL query string."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

    # Create a short-lived token scoped to this document
    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": str(current_user.id),
        "doc": document_id,
        "exp": expire,
        "scope": "preview",
    }
    from jose import jwt
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token}


@router.get("/{document_id}/onlyoffice-config")
async def get_onlyoffice_config(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build a view-mode OnlyOffice editor config for a file document."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

    if doc.file_type == "link":
        raise HTTPException(status_code=400, detail="链接型文档不支持 OnlyOffice 预览")
    ext = (doc.file_ext or "").lower()
    if ext not in _ONLYOFFICE_EXTS:
        raise HTTPException(status_code=400, detail="该格式不支持 OnlyOffice 预览")
    if not settings.ONLYOFFICE_URL or not settings.ONLYOFFICE_JWT_SECRET:
        raise HTTPException(status_code=503, detail="OnlyOffice 未配置")

    doc_url = f"{settings.ONLYOFFICE_INTERNAL_BASE}/api/onlyoffice/source/{make_source_token('doc', str(doc.id))}"
    oo_file_type = "txt" if ext == "md" else ext
    key = hashlib.sha256(
        f"{doc.id}:{doc.updated_at}:{doc.file_size}".encode("utf-8")
    ).hexdigest()[:40]

    config = {
        "document": {
            "fileType": oo_file_type,
            "key": key,
            "title": doc.title,
            "url": doc_url,
            "permissions": {
                "edit": False,
                "download": True,
                "print": True,
                "review": False,
                "comment": False,
            },
        },
        "documentType": _ONLYOFFICE_DOC_TYPE.get(ext, "word"),
        "editorConfig": {
            "mode": "view",
            "lang": "zh-CN",
            "user": {
                "id": str(current_user.id),
                "name": current_user.display_name or current_user.username,
            },
            "customization": {
                "autosave": False,
                "chat": False,
                "comments": False,
                "compactHeader": True,
                "compactToolbar": True,
                "hideRightMenu": True,
                "help": False,
                "plugins": False,
                "showReviewChanges": False,
                "spellcheck": False,
                "toolbarHideFileName": False,
            },
        },
    }
    from jose import jwt
    token = jwt.encode(config, settings.ONLYOFFICE_JWT_SECRET, algorithm="HS256")
    return {
        "documentServerUrl": settings.ONLYOFFICE_URL.rstrip("/"),
        "config": config,
        "token": token,
    }


@router.get("/{document_id}/download-token")
async def get_download_token(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a short-lived, single-document download token.

    Avoids exposing the full JWT in the browser navigation URL."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_download_document(doc):
        raise HTTPException(status_code=403, detail="无权下载该文档")

    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": str(current_user.id),
        "doc": document_id,
        "exp": expire,
        "scope": "download",
    }
    from jose import jwt
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token}


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    token: str = Query("", description="Short-lived download token (avoids exposing full JWT in URL)"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Return a presigned URL for direct file download from MinIO."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    # If token is passed via query param (browser navigation), use it to authenticate
    if token and not current_user:
        try:
            payload = decode_token(token)
            # Accept both scoped download tokens and full JWT tokens
            if payload.get("scope") == "download":
                if payload.get("doc") != document_id:
                    raise HTTPException(status_code=403, detail="下载令牌与文档不匹配")
            current_user = await db.get(User, payload["sub"])
            if not current_user or not current_user.is_active:
                raise HTTPException(status_code=403, detail="用户不存在或已停用")
        except HTTPException:
            raise HTTPException(status_code=401, detail="无效的令牌")

    perm = PermissionService(db, current_user)
    if not await perm.can_download_document(doc):
        raise HTTPException(status_code=403, detail="无权下载该文档")

    if doc.file_type == "link":
        raise HTTPException(status_code=400, detail="链接型文档不支持下载")

    # 下载量计数用原生 SQL 自增，避免 updated_at 被点击刷新
    await db.execute(
        text("UPDATE documents SET download_count = download_count + 1 WHERE id = :id"),
        {"id": doc.id},
    )
    await db.commit()
    await db.refresh(doc)

    download_url = await FileService.get_download_url(doc.original_path, doc.original_filename)
    return RedirectResponse(url=download_url)


@router.get("/{document_id}/stream")
async def stream_document(
    document_id: str,
    token: str = Query("", description="Short-lived token for media streaming"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Return an inline presigned URL for video/audio/image streaming (browser plays inline)."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    if token and not current_user:
        try:
            payload = decode_token(token)
            if payload.get("scope") == "download":
                if payload.get("doc") != document_id:
                    raise HTTPException(status_code=403, detail="令牌与文档不匹配")
            current_user = await db.get(User, payload["sub"])
            if not current_user or not current_user.is_active:
                raise HTTPException(status_code=403, detail="用户不存在或已停用")
        except HTTPException:
            raise HTTPException(status_code=401, detail="无效的令牌")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

    if doc.file_type == "link":
        raise HTTPException(status_code=400, detail="链接型文档不支持流式播放")

    # Generate inline presigned URL (browser displays, not download)
    stream_url = await FileService.get_preview_url(doc.original_path, doc.original_filename)
    return RedirectResponse(url=stream_url)
