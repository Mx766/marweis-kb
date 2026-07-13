from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, get_current_user_optional, require_role
from app.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.schemas import DocumentCreate, DocumentUpdate, DocumentItem, DocumentDetail, DocumentListResponse
from app.permissions import PermissionService, get_permission_service
from app.services.file_service import FileService
import uuid as _uuid
import os

router = APIRouter()


async def _doc_to_item(doc: Document, db: AsyncSession) -> DocumentItem:
    uploader = await db.get(User, doc.uploader_id)
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

    items = []
    for doc in docs:
        items.append(await _doc_to_item(doc, db))

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
    await db.flush()

    # Record browse history if logged in
    if current_user:
        from app.models.favorite import BrowseHistory
        from sqlalchemy import select as _sel2
        existing = (await db.execute(
            _sel2(BrowseHistory).where(
                BrowseHistory.user_id == current_user.id,
                BrowseHistory.document_id == doc.id,
            )
        )).scalar_one_or_none()
        if not existing:
            db.add(BrowseHistory(user_id=current_user.id, document_id=doc.id))

    await db.refresh(doc)
    await db.commit()

    item = await _doc_to_item(doc, db)
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
    import json
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
    return {"message": "文档已删除"}


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Return a presigned URL for inline preview (PDF in browser, not download)."""
    from fastapi.responses import RedirectResponse

    doc: Document | None = await db.get(Document, _uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="文档不存在")

    perm = PermissionService(db, current_user)
    if not await perm.can_view_document(doc):
        raise HTTPException(status_code=403, detail="无权查看该文档")

    if doc.file_type == "link":
        # Validate URL before redirect to prevent open redirect attacks
        target_url = doc.source_url or doc.original_path
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        if parsed.scheme and parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=400, detail="不支持的重定向协议")
        if parsed.netloc and not any(
            parsed.netloc == d or parsed.netloc.endswith("." + d) for d in (
                "nmpa.gov.cn", "cmde.org.cn", "samr.gov.cn",
                "fda.gov", "ecfr.gov", "eur-lex.europa.eu",
                "iso.org", "maris-reg.com",
            )
        ):
            raise HTTPException(status_code=400, detail="不支持的外部链接")
        return RedirectResponse(url=target_url)

    # If preview exists, use it; otherwise convert on-demand
    if doc.preview_path:
        preview_url = FileService.get_download_url(doc.preview_path, doc.original_filename)
        # For preview, don't force download — let browser display inline
        return RedirectResponse(url=preview_url)

    # On-demand conversion via Gotenberg
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        bucket_key = doc.original_path[5:]
        bucket, key = bucket_key.split("/", 1)
        resp = s3.get_object(Bucket=bucket, Key=key)
        file_content = resp["Body"].read()

        # Convert
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"files": (doc.original_filename, file_content)}
            convert_resp = await client.post(
                f"{settings.GOTENBERG_URL}/forms/libreoffice/convert",
                files=files,
            )
            if convert_resp.status_code == 200:
                import uuid as _uuid_module
                preview_key = f"previews/{_uuid_module.uuid4()}/{doc.original_filename.rsplit('.', 1)[0]}.pdf"
                from io import BytesIO
                s3.upload_fileobj(BytesIO(convert_resp.content), bucket, preview_key)
                doc.preview_path = f"s3://{bucket}/{preview_key}"
                await db.flush()
                await db.commit()

                preview_url = FileService.get_download_url(doc.preview_path, doc.original_filename)
                return RedirectResponse(url=preview_url)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Preview conversion failed for doc {document_id}: {e}")

    # Fallback: redirect to download
    return RedirectResponse(url=f"/api/documents/{document_id}/download")


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Return a presigned URL for direct file download from MinIO."""
    from fastapi.responses import RedirectResponse

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

    download_url = FileService.get_download_url(doc.original_path, doc.original_filename)
    return RedirectResponse(url=download_url)
