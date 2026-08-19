from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.document import Document
from app.config import settings
import uuid as _uuid
import boto3
from botocore.config import Config as BotoConfig
from app.auth import get_current_user, require_role, hash_password, validate_password_strength
from app.config import DEPARTMENTS, ROLES
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.favorite import BrowseHistory
from app.permissions import PermissionService
from app.schemas import UserCreate, UserUpdate, UserItem, UserListResponse
import uuid as _uuid
import datetime as _datetime
from app.services.search_service import index_document, remove_document
from app.services.markdown_service import queue_markdown_generation

router = APIRouter()

def _minio():
    ep = settings.MINIO_ENDPOINT
    return boto3.client("s3",
        endpoint_url=f"http://{ep}" if not settings.MINIO_SECURE else f"https://{ep}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"))


@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """Admin dashboard — overview stats, charts data, recent activity."""

    # dept_admin: filter to their department only
    doc_filter = [Document.is_deleted == False]
    user_filter = [User.is_active == True]
    if current_user.role == "dept_admin":
        perm = PermissionService(db, current_user)
        visible_cat_ids = await perm.get_visible_category_ids()
        doc_filter.append(Document.category_id.in_(visible_cat_ids))
        # Also include docs in public categories (visible_departments IS NULL)
        from app.models.category import Category as CatModel
        pub_cats = (await db.execute(
            select(CatModel.id).where(CatModel.visible_departments.is_(None))
        )).scalars().all()
        all_visible = list(set(visible_cat_ids + list(pub_cats)))
        doc_filter = [Document.is_deleted == False, Document.category_id.in_(all_visible)]
        user_filter.append(User.department == current_user.department)

    total_docs = (await db.execute(
        select(func.count(Document.id)).where(*doc_filter)
    )).scalar() or 0

    total_users = (await db.execute(
        select(func.count(User.id)).where(*user_filter)
    )).scalar() or 0

    # Categories: super_admin sees all, dept_admin sees visible + public
    if current_user.role == "dept_admin":
        total_cats = len(all_visible)
    else:
        total_cats = (await db.execute(select(func.count(Category.id)))).scalar() or 0

    total_views = (await db.execute(
        select(func.sum(Document.view_count)).where(*doc_filter)
    )).scalar() or 0

    total_downloads = (await db.execute(
        select(func.sum(Document.download_count)).where(*doc_filter)
    )).scalar() or 0

    # File type distribution
    file_type_stats = (await db.execute(
        select(Document.file_ext, func.count(Document.id))
        .where(*doc_filter)
        .group_by(Document.file_ext)
        .order_by(func.count(Document.id).desc())
        .limit(10)
    )).all()

    # Top categories by doc count
    cat_stats = (await db.execute(
        select(Category.name, func.count(Document.id))
        .join(Document, Document.category_id == Category.id, isouter=True)
        .where(*doc_filter)
        .group_by(Category.name)
        .order_by(func.count(Document.id).desc())
        .limit(10)
    )).all()

    # Daily uploads last 14 days
    fourteen_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)
    doc_date_filter = list(doc_filter) + [Document.created_at >= fourteen_ago]
    daily_uploads = (await db.execute(
        select(func.date(Document.created_at).label('day'), func.count(Document.id))
        .where(*doc_date_filter).group_by('day').order_by('day')
    )).all()

    # Users by role
    role_stats = (await db.execute(
        select(User.role, func.count(User.id)).where(*user_filter).group_by(User.role)
    )).all()

    # Users by department
    dept_stats = (await db.execute(
        select(User.department, func.count(User.id)).where(*user_filter).group_by(User.department)
    )).all()

    # Recent 10 docs
    recent_docs = (await db.execute(
        select(Document.title, Document.file_ext, Document.view_count, Document.updated_at)
        .where(*doc_filter).order_by(Document.updated_at.desc()).limit(8)
    )).all()

    return {
        "overview": {
            "total_docs": total_docs,
            "total_users": total_users,
            "total_categories": total_cats,
            "total_views": total_views or 0,
            "total_downloads": total_downloads or 0,
        },
        "file_types": [{"name": ext or "other", "count": cnt} for ext, cnt in file_type_stats],
        "top_categories": [{"name": name or "未分类", "count": cnt} for name, cnt in cat_stats],
        "daily_uploads": [{"date": str(day), "count": cnt} for day, cnt in daily_uploads],
        "roles": [{"name": r or "unknown", "count": cnt} for r, cnt in role_stats],
        "departments": [{"name": d or "unknown", "count": cnt} for d, cnt in dept_stats],
        "recent_docs": [
            {"title": t, "file_ext": e, "view_count": v, "updated_at": str(u)}
            for t, e, v, u in recent_docs
        ],
    }


def _user_to_item(user: User) -> UserItem:
    return UserItem(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        employee_id=user.employee_id,
        department=user.department,
        role=user.role,
        email=user.email,
        is_active=user.is_active,
        created_at=str(user.created_at),
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    department: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    conditions = []
    if department:
        conditions.append(User.department == department)
    if current_user.role == "dept_admin":
        conditions.append(User.department == current_user.department)

    query = select(User).where(*conditions).order_by(User.created_at.desc())
    count_query = select(func.count(User.id)).where(*conditions)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    users = result.scalars().all()

    items = [_user_to_item(u) for u in users]
    return UserListResponse(items=items, total=total, page=page, size=size)


@router.post("/users")
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Validate password strength
    pw_error = validate_password_strength(body.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    # Validate department and role
    if body.department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"无效的部门: {body.department}")
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {body.role}")

    # dept_admin can only create users in their own department with limited roles
    if current_user.role == "dept_admin":
        if body.department != current_user.department:
            raise HTTPException(status_code=403, detail="部门管理员只能在本部门创建用户")
        if body.role not in ("editor", "employee", "guest"):
            raise HTTPException(status_code=403, detail="部门管理员只能创建编辑者/员工/访客角色")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        employee_id=body.employee_id,
        department=body.department,
        role=body.role,
        email=body.email,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return _user_to_item(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "dept_admin":
        if user.department != current_user.department:
            raise HTTPException(status_code=403, detail="无权操作其他部门用户")
        # dept_admin cannot change a user's department to a different one
        if "department" in body.model_dump(exclude_unset=True):
            if body.department != current_user.department:
                raise HTTPException(status_code=403, detail="部门管理员不能将用户转移到其他部门")

    update_data = body.model_dump(exclude_unset=True)

    # Validate department and role if they are being updated
    if "department" in update_data and update_data["department"] not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"无效的部门: {update_data['department']}")
    if "role" in update_data and update_data["role"] not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {update_data['role']}")

    # dept_admin cannot escalate user to super_admin or dept_admin
    if current_user.role == "dept_admin" and "role" in update_data:
        if update_data["role"] not in ("editor", "employee", "guest"):
            raise HTTPException(status_code=403, detail="部门管理员不能授予此角色")
        # dept_admin cannot change role of super_admin or other dept_admins
        if user.role in ("super_admin", "dept_admin"):
            raise HTTPException(status_code=403, detail="无权修改管理员角色的用户")

    for key, val in update_data.items():
        setattr(user, key, val)
    await db.flush()
    await db.commit()
    return {"message": "更新成功"}


# ── 文档管理 CRUD ──


async def _admin_doc_visible(db: AsyncSession, user: User):
    """dept_admin 返回其可见分类集合；super_admin 返回 None 表示不限。"""
    if user.role == "super_admin":
        return None
    perm = PermissionService(db, user)
    return await perm.get_visible_category_ids()


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    q: str = Query(None), file_type: str = Query(None),
    sort: str = Query("updated_at"), order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    conditions = [Document.is_deleted == False]
    if current_user.role == "dept_admin":
        from sqlalchemy import false as sa_false

        visible = await _admin_doc_visible(db, current_user)
        if not visible:
            conditions.append(sa_false())
        else:
            conditions.append(Document.category_id.in_(visible))
    if q: conditions.append(Document.title.ilike(f"%{q}%"))
    if file_type:
        if file_type == 'link': conditions.append(Document.file_type == 'link')
        else: conditions.append(Document.file_ext.ilike(f"%{file_type}%"))
    count_q = select(func.count(Document.id)).where(*conditions)
    total = (await db.execute(count_q)).scalar() or 0
    sort_col = getattr(Document, sort, Document.updated_at)
    if order == 'asc': sort_col = sort_col.asc()
    else: sort_col = sort_col.desc()
    result = await db.execute(
        select(Document).where(*conditions).order_by(sort_col).offset((page-1)*size).limit(size))
    docs = result.scalars().all()
    uids = list({d.uploader_id for d in docs})
    umap = {}
    if uids:
        for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all():
            umap[str(u.id)] = u.display_name
    items = [{"id":str(d.id),"title":d.title,"file_type":d.file_type,"file_ext":d.file_ext,
              "uploader_name":umap.get(str(d.uploader_id),""),"updated_at":d.updated_at.isoformat(),
              "view_count":d.view_count,"summary":d.summary,"source":d.source,"category_id":str(d.category_id) if d.category_id else None,"tags":d.tags or []} for d in docs]
    return {"items":items,"total":total,"page":page,"size":size}

@router.put("/documents/{doc_id}")
async def update_document(doc_id:str, body:dict, db:AsyncSession=Depends(get_db),
    current_user:User=Depends(require_role("super_admin","dept_admin"))):
    d = (await db.execute(select(Document).where(Document.id==_uuid.UUID(doc_id)))).scalar()
    if not d: raise HTTPException(404,"文档不存在")
    perm = PermissionService(db, current_user)
    if not await perm.can_edit_document(d):
        raise HTTPException(403,"无权编辑该文档")
    if 'category_id' in body and body['category_id']:
        try:
            new_cat = _uuid.UUID(body['category_id'])
        except (ValueError, AttributeError):
            raise HTTPException(400,"无效的分类ID")
        cat = await db.get(Category, new_cat)
        if not cat:
            raise HTTPException(400,"指定的分类不存在")
        if current_user.role != "super_admin":
            visible = await perm.get_visible_category_ids()
            if new_cat not in visible:
                raise HTTPException(403,"无权将文档移动到该分类")
    for k in ('title','summary','source','tags'):
        if k in body: setattr(d, k, body[k])
    if 'category_id' in body and body['category_id']:
        d.category_id = new_cat
    await db.commit()
    try:
        await index_document(d)
    except Exception:
        pass
    return {"ok":True}

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id:str, db:AsyncSession=Depends(get_db),
    current_user:User=Depends(require_role("super_admin","dept_admin"))):
    d = (await db.execute(select(Document).where(Document.id==_uuid.UUID(doc_id)))).scalar()
    if not d: raise HTTPException(404,"文档不存在")
    perm = PermissionService(db, current_user)
    if not await perm.can_delete_document(d):
        raise HTTPException(403,"无权删除该文档")
    d.is_deleted = True; await db.commit()
    try:
        await remove_document(str(d.id))
    except Exception:
        pass
    return {"ok":True}

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), title: str = Form(...),
    category_id: str = Form(""), tags: str = Form(""), summary: str = Form(""),
    source: str = Form(""), db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin"))):
    content = await file.read()
    ext = file.filename.rsplit(".",1)[-1].lower() if "." in file.filename else ""
    cat_uuid = None
    if category_id:
        try:
            cat_uuid = _uuid.UUID(category_id)
        except (ValueError, AttributeError):
            raise HTTPException(400,"无效的分类ID")
        cat = await db.get(Category, cat_uuid)
        if not cat:
            raise HTTPException(400,"指定的分类不存在")
    if current_user.role != "super_admin":
        if cat_uuid is None:
            raise HTTPException(400,"部门管理员上传必须指定分类")
        visible = await _admin_doc_visible(db, current_user)
        if cat_uuid not in (visible or []):
            raise HTTPException(403,"无权上传到该分类")
    obj_key = f"documents/{_uuid.uuid4().hex}.{ext}"
    try:
        _minio().put_object(Bucket=settings.MINIO_BUCKET, Key=obj_key, Body=content,
            ContentType=file.content_type or "application/octet-stream")
    except Exception as e: raise HTTPException(500,f"存储失败:{e}")
    doc = Document(title=title,file_type="file",original_filename=file.filename,file_size=len(content),
        file_ext=ext,mime_type=file.content_type or "",original_path=f"s3://{settings.MINIO_BUCKET}/{obj_key}",uploader_id=current_user.id,
        category_id=cat_uuid,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        summary=summary,source=source)
    db.add(doc); await db.commit(); await db.refresh(doc)
    try:
        await index_document(doc)
        queue_markdown_generation(str(doc.id))
    except Exception:
        pass
    return {"id":str(doc.id),"title":doc.title}

@router.post("/documents/link")
async def add_link(body:dict, db:AsyncSession=Depends(get_db),
    current_user:User=Depends(require_role("super_admin","dept_admin"))):
    cat_uuid = None
    if body.get("category_id"):
        try:
            cat_uuid = _uuid.UUID(body["category_id"])
        except (ValueError, AttributeError):
            raise HTTPException(400,"无效的分类ID")
        cat = await db.get(Category, cat_uuid)
        if not cat:
            raise HTTPException(400,"指定的分类不存在")
    if current_user.role != "super_admin":
        if cat_uuid is None:
            raise HTTPException(400,"部门管理员必须指定分类")
        visible = await _admin_doc_visible(db, current_user)
        if cat_uuid not in (visible or []):
            raise HTTPException(403,"无权在该分类创建链接文档")
    source_url = body.get("source_url","")
    doc = Document(title=body.get("title",""),file_type="link",original_filename=body.get("title",""),
        original_path=source_url or body.get("title",""),
        file_ext="link",mime_type="text/html",
        source_url=source_url,uploader_id=current_user.id,
        category_id=cat_uuid,
        tags=[t.strip() for t in body.get("tags","").split(",") if t.strip()] if body.get("tags") else [],
        summary=body.get("summary",""),source=body.get("source",""))
    db.add(doc); await db.commit(); await db.refresh(doc)
    try:
        await index_document(doc)
        queue_markdown_generation(str(doc.id))
    except Exception:
        pass
    return {"id":str(doc.id),"title":doc.title}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    await db.delete(user)
    await db.flush()
    await db.commit()
    return {"message": "用户已删除"}


# ── 访问记录 ──────────────────────────────────────────────


@router.get("/activity/users")
async def admin_activity_users(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """活跃用户排行：按浏览记录数排序，附最近访问时间。"""
    conds = [User.is_active == True]
    if current_user.role == "dept_admin":
        conds.append(User.department == current_user.department)
    if q:
        conds.append(
            User.display_name.ilike(f"%{q}%") | User.username.ilike(f"%{q}%")
        )
    rows = (
        await db.execute(
            select(
                User.id,
                User.display_name,
                User.username,
                User.department,
                User.role,
                func.count(BrowseHistory.id).label("views"),
                func.max(BrowseHistory.created_at).label("last_active"),
            )
            .outerjoin(BrowseHistory, BrowseHistory.user_id == User.id)
            .where(*conds)
            .group_by(User.id)
            .order_by(func.count(BrowseHistory.id).desc(), User.display_name)
            .limit(limit)
        )
    ).all()
    return {
        "items": [
            {
                "id": str(r[0]),
                "display_name": r[1],
                "username": r[2],
                "department": r[3],
                "role": r[4],
                "views": r[5] or 0,
                "last_active": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


@router.get("/activity/records")
async def admin_activity_records(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """最近访问记录流水（用户/文档/时间）。"""
    user_conds = []
    if current_user.role == "dept_admin":
        user_conds.append(User.department == current_user.department)
    base = (
        select(
            BrowseHistory,
            User.display_name,
            User.department,
            Document.title,
            Category.name,
        )
        .join(User, User.id == BrowseHistory.user_id)
        .join(Document, Document.id == BrowseHistory.document_id)
        .join(Category, Category.id == Document.category_id, isouter=True)
        .where(*user_conds, Document.is_deleted == False)
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(BrowseHistory.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return {
        "items": [
            {
                "user_id": str(bh.user_id),
                "user_name": name,
                "department": dept,
                "doc_id": str(bh.document_id),
                "doc_title": title,
                "category": cat,
                "created_at": bh.created_at.isoformat() if bh.created_at else None,
            }
            for bh, name, dept, title, cat in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/activity/users/{user_id}/records")
async def admin_user_records(
    user_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """单个用户的浏览记录。"""
    try:
        user_uuid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="用户不存在")
    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "dept_admin" and user.department != current_user.department:
        raise HTTPException(status_code=403, detail="无权查看其他部门")
    base = (
        select(BrowseHistory, Document.title, Category.name)
        .join(Document, Document.id == BrowseHistory.document_id)
        .join(Category, Category.id == Document.category_id, isouter=True)
        .where(
            BrowseHistory.user_id == user_uuid,
            Document.is_deleted == False,
        )
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(BrowseHistory.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return {
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "username": user.username,
            "department": user.department,
            "role": user.role,
        },
        "items": [
            {
                "doc_id": str(bh.document_id),
                "doc_title": title,
                "category": cat,
                "created_at": bh.created_at.isoformat() if bh.created_at else None,
            }
            for bh, title, cat in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/activity/hot")
async def admin_activity_hot(
    sort: str = Query("views", pattern="^(views|downloads)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """热门文档排行：按浏览量或下载量。"""
    col = Document.view_count if sort == "views" else Document.download_count
    doc_filter = [Document.is_deleted == False]
    if current_user.role == "dept_admin":
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        if not visible:
            return {"items": []}
        doc_filter.append(Document.category_id.in_(visible))
    rows = (
        await db.execute(
            select(Document.title, Document.file_ext, col, Category.name)
            .join(Category, Category.id == Document.category_id, isouter=True)
            .where(*doc_filter)
            .order_by(col.desc())
            .limit(limit)
        )
    ).all()
    return {
        "items": [
            {
                "title": r[0],
                "file_ext": r[1],
                "count": r[2] or 0,
                "category": r[3],
            }
            for r in rows
        ]
    }


@router.get("/activity/logs")
async def admin_activity_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    """公盘操作审计日志。"""
    dept = None if current_user.role == "super_admin" else current_user.department
    pattern = f"%{q}%" if q else None
    conds: list[str] = []
    params: dict = {"size": size, "off": (page - 1) * size}
    if dept:
        conds.append("u.department = :dept")
        params["dept"] = dept
    if pattern:
        conds.append(
            "(l.filename ILIKE :p OR u.display_name ILIKE :p OR l.username ILIKE :p)"
        )
        params["p"] = pattern
    where = " AND ".join(conds) if conds else "TRUE"
    total = (
        await db.execute(
            text(
                "SELECT count(*) FROM user_file_logs l LEFT JOIN users u ON u.id = l.user_id "
                f"WHERE {where}"
            ),
            params,
        )
    ).scalar_one()
    rows = (
        await db.execute(
            text(
                "SELECT l.id, l.username, u.display_name AS uname, u.department, "
                "l.action, l.filename, l.detail, l.created_at "
                "FROM user_file_logs l LEFT JOIN users u ON u.id = l.user_id "
                f"WHERE {where} ORDER BY l.created_at DESC LIMIT :size OFFSET :off"
            ),
            params,
        )
    ).all()
    return {
        "items": [
            {
                "id": r[0],
                "username": r[1],
                "user_name": r[2] or r[1],
                "department": r[3],
                "action": r[4],
                "filename": r[5],
                "detail": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }
