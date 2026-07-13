import json
import logging
import uuid as _uuid
from io import BytesIO
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user, get_current_user_optional, require_role, decode_token
from app.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.favorite import BrowseHistory
from app.schemas import DocumentCreate, DocumentUpdate, DocumentItem, DocumentDetail, DocumentListResponse
from app.permissions import PermissionService, get_permission_service
from app.services.file_service import FileService, get_minio_client, _run_in_thread
from app.services.search_service import index_document, remove_document

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
    "maris-reg.com", "www.maris-reg.com",
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


# ═══════════════════════════════════════════════════════════════
# Document endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("")
async def list_documents(
    category_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("updated_at", pattern="^(updated_at|created_at|title|file_size)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    conditions = [Document.is_deleted == False]
    if category_id:
        conditions.append(Document.category_id == _uuid.UUID(category_id))

    # Permission-based category filtering
    perm = PermissionService(db, current_user)
    visible_ids = await perm.get_visible_category_ids()

    if current_user and current_user.role == "super_admin":
        pass  # Super admin sees all documents — no extra filter needed
    elif visible_ids:
        conditions.append(Document.category_id.in_(visible_ids))
    else:
        # User has no visible categories at all — return empty list
        conditions.append(Document.category_id.is_(None))

    sort_col = getattr(Document, sort)
    if order == "desc":
        sort_col = sort_col.desc()

    query = select(Document).where(*conditions).order_by(sort_col)
    count_query = select(func.count(Document.id)).where(*conditions)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    docs = result.scalars().all()

    # Batch-load all uploaders in a single query (eliminates N+1)
    uploader_map = await _batch_load_uploaders(db, docs)

    items = [_doc_to_item(doc, uploader_map.get(doc.uploader_id)) for doc in docs]

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

    doc.view_count += 1

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
    return DocumentDetail(
        **item.model_dump(),
        preview_path=doc.preview_path,
        original_path=doc.original_path,
        download_count=doc.download_count,
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
    current_user: User = Depends(require_role("super_admin", "dept_admin", "editor")),
):
    """Upload a file or create a link-based document entry."""
    tag_list = json.loads(tags) if isinstance(tags, str) else (tags or [])

    if file:
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
            effective_date=effective_date,
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
            effective_date=effective_date,
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
    for key, val in update_data.items():
        setattr(doc, key, val)
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

    Accepts token via query parameter because browser iframe requests
    don't carry the Authorization header.
    """
    from fastapi.responses import StreamingResponse

    # Authenticate via token query param (fallback to header for backward compat)
    if token:
        try:
            payload = decode_token(token)
        except HTTPException:
            raise HTTPException(status_code=401, detail="无效的预览令牌")
        current_user = await db.get(User, payload["sub"])
        if not current_user or not current_user.is_active:
            raise HTTPException(status_code=403, detail="用户不存在或已停用")
    else:
        # No token at all → guest
        current_user = None

    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

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
    elif doc.file_ext in _CONVERTIBLE_EXTS:
        # Convert on-demand via Gotenberg
        preview_content = await _convert_and_cache(doc, db)

    if preview_content:
        return StreamingResponse(
            BytesIO(preview_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{doc.title}.pdf"'},
        )

    # Last resort: redirect to raw file download
    if doc.original_path.startswith("s3://"):
        url = await FileService.get_download_url(doc.original_path, doc.original_filename)
        return RedirectResponse(url=url)
    raise HTTPException(status_code=400, detail="该文档不支持在线预览")


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Return a presigned URL for direct file download from MinIO."""
    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权下载该文档")

    if doc.file_type == "link":
        raise HTTPException(status_code=400, detail="链接型文档不支持下载")

    # Increment download count
    doc.download_count += 1
    await db.flush()
    await db.commit()

    download_url = await FileService.get_download_url(doc.original_path, doc.original_filename)
    return RedirectResponse(url=download_url)
