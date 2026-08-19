"""资料管理系统 API — 文件夹/上传/批量/回收站"""
import asyncio
import logging
import re
import time
import uuid as _uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, func, and_, or_, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, async_session_maker
from app.auth import get_current_user, get_current_user_optional, decode_token
from app.models.user import User
from app.models.user_file import UserFile
from app.config import settings, DEPARTMENTS
from app.api.oo_source import make_source_token
from app.services.file_service import (
    FileService,
    get_minio_client,
    _get_presigned_client,
    _ensure_bucket_exists,
    _run_in_thread,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

OFFICE_PREVIEW_EXTS = {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'txt', 'csv'}

# 后台转换状态（避免重复转换，转换失败 24h 内不反复尝试）
_CONVERTING_FILES: dict[str, float] = {}
_CONVERT_TASKS_FILES: set[asyncio.Task] = set()
_CONVERT_FAILED_FILES: dict[str, float] = {}
_CONVERT_FAIL_TTL = 24 * 3600
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _read_minio_object(s3, key: str) -> bytes | None:
    try:
        obj = s3.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
        return obj["Body"].read()
    except Exception:
        return None


async def _convert_and_cache_file(file_id: str) -> None:
    """公盘 Office → PDF：Gotenberg 转换并缓存到 MinIO，供预览复用。"""
    try:
        async with async_session_maker() as db:
            f = (
                await db.execute(
                    select(UserFile).where(
                        UserFile.id == _parse_uuid(file_id, "文件ID"),
                        UserFile.is_deleted == False,
                        UserFile.is_folder == False,
                    )
                )
            ).scalar_one_or_none()
            if not f:
                return
            filename = f.filename or "file"
            mime = f.mime_type or "application/octet-stream"
            s3 = get_minio_client()
            obj = s3.get_object(Bucket=settings.MINIO_BUCKET, Key=f.file_path)
            content = obj["Body"].read()

        import httpx
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.GOTENBERG_URL}/forms/libreoffice/convert",
                files={"files": (filename, content, mime)},
            )
            if resp.status_code != 200:
                _CONVERT_FAILED_FILES[file_id] = time.time()
                return

        cache_key = f"previews/userfiles/{file_id}.pdf"
        await _run_in_thread(
            lambda: s3.put_object(
                Bucket=settings.MINIO_BUCKET,
                Key=cache_key,
                Body=resp.content,
                ContentType="application/pdf",
            )
        )
    except Exception:
        logger.warning("Preview conversion failed for file %s", file_id, exc_info=True)
        _CONVERT_FAILED_FILES[file_id] = time.time()
    finally:
        _CONVERTING_FILES.pop(file_id, None)


async def _log_op(
    user: User,
    action: str,
    filename: str = "",
    file_id=None,
    detail: str = "",
) -> None:
    try:
        async with async_session_maker() as db:
            await db.execute(
                text(
                    "INSERT INTO user_file_logs (user_id, username, action, file_id, filename, detail) "
                    "VALUES (:uid, :un, :a, :fid, :fn, :d)"
                ),
                {
                    "uid": user.id,
                    "un": user.username,
                    "a": action,
                    "fid": file_id,
                    "fn": filename[:500],
                    "d": detail[:1000],
                },
            )
            await db.commit()
            # 写操作后使总览/统计缓存失效，保证上传后界面自动刷新
            _OVERVIEW_CACHE.clear()
            _STATS_CACHE.clear()
    except Exception:
        logger.warning("Failed to write user_file_log", exc_info=True)

# 概览接口短缓存：导入/机械盘繁忙时避免每次进页面都做全表聚合
_OVERVIEW_TTL = 60
_OVERVIEW_CACHE: dict[str, tuple[float, dict]] = {}
_STATS_CACHE: dict[str, tuple[float, dict]] = {}

# ── Pydantic models ──
class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None
    department: str | None = None
    scope: str = "dept"

class FolderRename(BaseModel):
    name: str
    employee_download: bool | None = None

class BatchDelete(BaseModel):
    ids: list[str]

class BatchMove(BaseModel):
    ids: list[str]
    target_folder_id: str | None = None


def _parse_uuid(value: str, field: str = "ID") -> _uuid.UUID:
    """Parse a UUID string, raising a 400 on malformed input."""
    try:
        return _uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(400, f"无效的{field}: {value}")


def _parse_uuid_list(ids: list[str], field: str = "ID") -> list[_uuid.UUID]:
    out = []
    for i in ids:
        out.append(_parse_uuid(i, field))
    return out


def _file_dict(f: UserFile, uploader_name: str = "", can_write: bool = True, starred: bool = False) -> dict:
    return {
        "id": str(f.id), "user_id": str(f.user_id),
        "filename": f.filename, "original_filename": f.original_filename,
        "file_size": f.file_size, "file_ext": f.file_ext, "mime_type": f.mime_type,
        "department": f.department, "is_folder": f.is_folder,
        "child_count": None, "child_size": None,
        "employee_download": bool(getattr(f, "employee_download", True)),
        "scope": f.scope,
        "visible_departments": f.visible_departments or None,
        "visible_user_ids": f.visible_user_ids or None,
        "admin_only": bool(getattr(f, "admin_only", False)),
        "parent_id": str(f.parent_id) if f.parent_id else None,
        "in_trash": f.in_trash,
          "uploader_name": uploader_name,
          "can_write": can_write,
          "starred": starred,
          "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }


async def _folder_agg_stats(
    db: AsyncSession,
    folder_ids: list[_uuid.UUID],
    current_user: User,
    in_trash: bool = False,
) -> dict[str, dict]:
    """One-pass recursive stats: file count and total size under each folder (visible scope only)."""
    if not folder_ids or in_trash:
        return {}
    cond_sql = "uf.is_deleted = false AND uf.in_trash = false"
    params: dict = {"ids": list(folder_ids)}
    if current_user.role != "super_admin":
        dept = current_user.department or ""
        params["dept"] = dept
        if current_user.role == "dept_admin":
            cond_sql += " AND uf.department = :dept"
        elif current_user.role in ("editor", "employee"):
            params["uid"] = str(current_user.id)
            cond_sql += (
                " AND uf.department = :dept AND uf.admin_only = false "
                "AND (uf.scope IN ('dept','all') "
                "OR (uf.scope='specific' AND jsonb_exists(uf.visible_departments::jsonb, :dept)))"
            )
        else:
            params["uid"] = str(current_user.id)
            cond_sql += " AND uf.user_id = :uid"
    sql = text(f"""
        WITH RECURSIVE tree AS (
            SELECT id, parent_id, is_folder, file_size, ARRAY[]::uuid[] AS anc
            FROM user_files
            WHERE id = ANY(:ids) AND is_deleted = false AND in_trash = false
            UNION ALL
            SELECT uf.id, uf.parent_id, uf.is_folder, uf.file_size, tree.anc || uf.parent_id
            FROM user_files uf
            JOIN tree ON uf.parent_id = tree.id
            WHERE {cond_sql}
        )
        SELECT a.folder_id, count(*) AS cnt, coalesce(sum(a.fsz), 0) AS total
        FROM (
            SELECT unnest(tree.anc) AS folder_id, tree.file_size AS fsz
            FROM tree
            WHERE tree.is_folder = false
        ) a
        GROUP BY a.folder_id
    """)
    rows = (await db.execute(sql, params)).all()
    return {
        str(r[0]): {"child_count": int(r[1]), "child_size": int(r[2] or 0)}
        for r in rows
    }


# ── 权限 ──
def _visible_scope_cond(dept: str):
    """部门级可见性条件：本部门 / 全员 / 指定部门包含该部门（不含 admin_only）。"""
    return or_(
        UserFile.scope == "dept",
        UserFile.scope == "all",
        and_(
            UserFile.scope == "specific",
            func.jsonb_exists(UserFile.visible_departments.cast(JSONB), dept),
        ),
    )


def _perm_filter(query, user: User):
    """列表可见性：超管全部；部门管理员看本部门+共享到本部门/指定本人；员工看可见范围+指定本人。"""
    if user.role == "super_admin":
        return query
    dept = user.department or ""
    if user.role == "dept_admin":
        return query.where(
            or_(
                UserFile.department == dept,  # 本部门全部（含仅管理员）
                and_(
                    UserFile.scope == "specific",
                    func.jsonb_exists(UserFile.visible_departments.cast(JSONB), dept),
                ),
                and_(
                    UserFile.scope == "users",
                    UserFile.visible_user_ids.isnot(None),
                    func.jsonb_exists(UserFile.visible_user_ids.cast(JSONB), str(user.id)),
                ),
            )
        )
    if user.role in ("editor", "employee"):
        return query.where(
            or_(
                and_(UserFile.department == dept, _visible_scope_cond(dept), UserFile.admin_only == False),
                and_(
                    UserFile.scope == "specific",
                    func.jsonb_exists(UserFile.visible_departments.cast(JSONB), dept),
                    UserFile.admin_only == False,
                ),
                and_(UserFile.scope == "all", UserFile.department != dept, UserFile.admin_only == False),
                and_(
                    UserFile.scope == "users",
                    or_(
                        UserFile.user_id == user.id,
                        and_(
                            UserFile.visible_user_ids.isnot(None),
                            func.jsonb_exists(UserFile.visible_user_ids.cast(JSONB), str(user.id)),
                        ),
                    ),
                ),
                and_(UserFile.scope == "private", UserFile.user_id == user.id),
            ),
        )
    return query.where(UserFile.user_id == user.id)


def _can_read(f: UserFile, user: User) -> bool:
    """Read (download/preview) scope, kept consistent with the list scope."""
    if user.role == "super_admin":
        return True
    dept = user.department or ""
    if f.scope == "users":
        return f.user_id == user.id or bool(f.visible_user_ids and str(user.id) in f.visible_user_ids)
    if user.role == "dept_admin":
        return f.department == dept or (
            f.scope == "specific"
            and f.visible_departments
            and dept in f.visible_departments
        )
    if user.role in ("editor", "employee"):
        if f.scope == "private":
            return f.user_id == user.id
        if f.admin_only:
            return False
        if f.department != dept:
            # 其他部门：全员可见 / 指定了本部门可见
            return f.scope == "all" or bool(
                f.scope == "specific" and f.visible_departments and dept in f.visible_departments
            )
        if f.scope == "dept":
            return True
        if f.scope == "all":
            return True
        return bool(f.visible_departments and dept in f.visible_departments)
    return f.user_id == user.id


def _can_download(f: UserFile, user: User) -> bool:
    """Download permission: admins/uploader always; employees only when employee_download enabled."""
    if user.role == "super_admin":
        return True
    if user.role == "dept_admin" and f.department == (user.department or ""):
        return True
    if f.user_id == user.id:
        return True
    if f.scope == "private":
        return f.user_id == user.id
    if not _can_read(f, user):
        return False
    return bool(getattr(f, "employee_download", True))


def _can_write(f: UserFile, user: User) -> bool:
    """Manage (rename/delete/move/upload-into) permission."""
    if user.role == "super_admin":
        return True
    if f.department != (user.department or ""):
        return False
    if user.role == "dept_admin":
        return True
    return f.user_id == user.id


def _can_upload_into(f: UserFile, user: User) -> bool:
    """Upload/create-folder permission: any member of the folder's department may add to it."""
    if user.role == "super_admin":
        return True
    if f.department != (user.department or ""):
        return False
    if user.role == "dept_admin":
        return True
    # 员工：公盘可传；私盘文件夹只能传自己的
    if f.scope == "private":
        return f.user_id == user.id
    return True


# ── 树操作辅助 ──
async def _collect_descendant_ids(db: AsyncSession, root_ids: list[_uuid.UUID]) -> list[_uuid.UUID]:
    """Collect all descendant IDs in one recursive SQL query.

    The previous Python loop built an IN (...) list that could exceed
    PostgreSQL's 32767 argument limit on huge folders (e.g. 49k+ files),
    causing a 500 on delete/move/restore. A recursive CTE has no such limit.
    """
    if not root_ids:
        return []
    stmt = text(
        """
        WITH RECURSIVE tree AS (
            SELECT id, parent_id FROM user_files
            WHERE id = ANY(:roots) AND is_deleted = false
            UNION
            SELECT uf.id, uf.parent_id FROM user_files uf
            JOIN tree t ON uf.parent_id = t.id
            WHERE uf.is_deleted = false
        )
        SELECT id FROM tree
        """
    )
    result = await db.execute(stmt, {"roots": root_ids})
    return [row[0] for row in result.all()]


async def _fetch_rows_by_ids(
    db: AsyncSession,
    ids: list[_uuid.UUID],
    *extra_conditions,
) -> list[UserFile]:
    """Fetch ORM rows by ids in chunks (avoids the 32767-argument limit)."""
    rows: list[UserFile] = []
    for i in range(0, len(ids), 4000):
        chunk = ids[i : i + 4000]
        result = await db.execute(
            select(UserFile).where(
                UserFile.id.in_(chunk),
                UserFile.is_deleted == False,
                *extra_conditions,
            )
        )
        rows.extend(result.scalars().all())
    return rows


async def _update_descendants(
    db: AsyncSession,
    root_ids: list[_uuid.UUID],
    *,
    in_trash: bool | None = None,
    is_deleted: bool | None = None,
) -> int:
    """Bulk-update a folder subtree via one recursive CTE (no IN-limit)."""
    if not root_ids:
        return 0
    sets = []
    if in_trash is not None:
        sets.append("in_trash = :in_trash")
        if in_trash:
            sets.append("trashed_at = now()")
        else:
            sets.append("trashed_at = NULL")
    if is_deleted is not None:
        sets.append("is_deleted = :is_deleted")
    if not sets:
        return 0
    stmt = text(
        """
        WITH RECURSIVE tree AS (
            SELECT id, parent_id FROM user_files
            WHERE id = ANY(:roots) AND is_deleted = false
            UNION
            SELECT uf.id, uf.parent_id FROM user_files uf
            JOIN tree t ON uf.parent_id = t.id
            WHERE uf.is_deleted = false
        )
        UPDATE user_files uf
        SET """ + ", ".join(sets) + """
        FROM tree t
        WHERE uf.id = t.id
        """
    )
    params: dict = {"roots": root_ids}
    if in_trash is not None:
        params["in_trash"] = in_trash
    if is_deleted is not None:
        params["is_deleted"] = is_deleted
    result = await db.execute(stmt, params)
    return result.rowcount or 0


async def _is_descendant(db: AsyncSession, node_id: _uuid.UUID, ancestor_id: _uuid.UUID) -> bool:
    """Return True if node_id is `ancestor_id` itself or under it (walking up parent chain)."""
    cur: _uuid.UUID | None = node_id
    seen: set[_uuid.UUID] = set()
    while cur:
        if cur == ancestor_id:
            return True
        if cur in seen:
            return False
        seen.add(cur)
        row = (await db.execute(select(UserFile.parent_id).where(UserFile.id == cur))).scalar()
        if row is None:
            return False
        cur = row
    return False


async def _delete_minio_objects(rows: list[UserFile]) -> int:
    """Best-effort batch delete of MinIO objects for non-folder rows. Returns deleted count."""
    keys = [f.file_path for f in rows if not f.is_folder and f.file_path]
    return await _delete_minio_keys(keys)


async def _delete_minio_keys(keys: list[str]) -> int:
    """Delete MinIO objects in batches of 1000 (best-effort)."""
    if not keys:
        return 0
    s3 = get_minio_client()
    deleted = 0
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i:i + 1000]]
        try:
            resp = await _run_in_thread(
                s3.delete_objects,
                Bucket=settings.MINIO_BUCKET,
                Delete={"Objects": batch, "Quiet": True},
            )
            deleted += len(batch) - len(resp.get("Errors", []) or [])
        except Exception:
            logger.warning("Failed to batch-delete %d MinIO objects", len(batch), exc_info=True)
    return deleted


# ── API ──

@router.get("")
async def list_files(
    parent_id: str | None = Query(None),
    department: str | None = Query(None),
    user_id: str | None = Query(None),
    scope: str | None = Query(None),
    my: bool = Query(False),
    shared: bool = Query(False),
    root: bool = Query(False),
    in_trash: bool = Query(False),
    keyword: str = Query(None),
    file_type: str = Query(None),
    sort: str = Query("name"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出文件/文件夹"""
    conditions = [UserFile.is_deleted == False, UserFile.in_trash == in_trash]

    if shared:
        # 跨部门共享视图：显式标记为共享（全员/指定部门/指定人员）的文件
        dept = current_user.department or ""
        conditions.append(UserFile.is_folder == False)
        conditions.append(
            or_(
                UserFile.scope == "all",
                and_(
                    UserFile.scope == "specific",
                    func.jsonb_exists(UserFile.visible_departments.cast(JSONB), dept),
                ),
                and_(
                    UserFile.scope == "users",
                    UserFile.visible_user_ids.isnot(None),
                    func.jsonb_exists(UserFile.visible_user_ids.cast(JSONB), str(current_user.id)),
                ),
            )
        )
        if current_user.role in ("editor", "employee", "dept_admin"):
            conditions.append(UserFile.department != dept)
    elif user_id:
        conditions.append(UserFile.user_id == _parse_uuid(user_id, "用户ID"))
    if scope:
        conditions.append(UserFile.scope == scope)

    if shared:
        pass  # 共享视图条件已在上方设置，跳过下方 parent/department 分支
    elif my:
        conditions.append(UserFile.user_id == current_user.id)
        conditions.append(UserFile.scope == "private")
        if parent_id:
            try:
                conditions.append(UserFile.parent_id == _uuid.UUID(parent_id))
            except ValueError:
                return {"items": [], "total": 0, "breadcrumb": [{"id": None, "name": "根目录"}],
                        "page": page, "size": size}
        else:
            # 私盘根视图：只显示根级文件夹/文件，进入文件夹后再看内容
            conditions.append(UserFile.parent_id == None)
    elif department:
        conditions.append(UserFile.department == department)
        if parent_id:
            # 带 department 时也必须应用 parent_id 过滤，否则主管查看员工私盘子文件夹会列出整个私盘
            try:
                conditions.append(UserFile.parent_id == _uuid.UUID(parent_id))
            except ValueError:
                return {"items": [], "total": 0, "breadcrumb": [{"id": None, "name": "根目录"}],
                        "page": page, "size": size}
        elif scope == "private":
            # 私盘视图（含主管查看员工私盘）根级只显示根目录
            conditions.append(UserFile.parent_id == None)
        elif root:
            # 部门根视图：显示全部根级文件夹/文件（部门可能有多个根目录）
            conditions.append(UserFile.parent_id == None)
    elif parent_id:
        # 回收站视图：忽略 parent 过滤，展示全部已回收项（否则文件夹内的文件永远看不到）
        if not in_trash:
            try:
                conditions.append(UserFile.parent_id == _uuid.UUID(parent_id))
            except ValueError:
                return {"items": [], "total": 0, "breadcrumb": [{"id": None, "name": "根目录"}],
                        "page": page, "size": size}
    elif not in_trash:
        conditions.append(UserFile.parent_id == None)

    if keyword:
        conditions.append(UserFile.filename.ilike(f"%{keyword}%"))

    if file_type:
        exts = _TYPE_EXTS.get(file_type)
        if exts:
            conditions.append(UserFile.file_ext.in_(exts))
        elif file_type == "other":
            all_exts = set().union(*_TYPE_EXTS.values())
            conditions.append(
                or_(
                    UserFile.file_ext.is_(None),
                    UserFile.file_ext.notin_(all_exts),
                )
            )
        else:
            raise HTTPException(400, "无效的文件类型筛选")

    base = select(UserFile).where(*conditions)
    base = _perm_filter(base, current_user)

    # 排序
    if sort == "size":
        base = base.order_by(UserFile.file_size.desc())
    elif sort == "date":
        base = base.order_by(UserFile.updated_at.desc())
    elif sort == "type":
        base = base.order_by(UserFile.file_ext)
    else:
        base = base.order_by(UserFile.is_folder.desc(), UserFile.filename)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(base.offset((page - 1) * size).limit(size))
    files = result.scalars().all()

    # 加载用户名
    uid_map = {}
    uids = list({f.user_id for f in files})
    if uids:
        ur = await db.execute(select(User).where(User.id.in_(uids)))
        for u in ur.scalars().all():
            uid_map[str(u.id)] = u.display_name

    starred_ids: set[str] = set()
    try:
        sr = await db.execute(
            text("SELECT file_id FROM file_stars WHERE user_id = :uid"),
            {"uid": current_user.id},
        )
        starred_ids = {str(x[0]) for x in sr.all()}
    except Exception:
        starred_ids = set()  # 表不存在时忽略
    items = [
        _file_dict(
            f, uid_map.get(str(f.user_id), ""),
            _can_write(f, current_user),
            starred=str(f.id) in starred_ids,
        )
        for f in files
    ]
    # fill folder row stats: file count and total size (one recursive query)
    folder_ids = [f.id for f in files if f.is_folder]
    if folder_ids:
        agg = await _folder_agg_stats(db, folder_ids, current_user, in_trash)
        for it in items:
            if it["is_folder"]:
                s = agg.get(it["id"], {})
                it["child_count"] = s.get("child_count", 0)
                it["child_size"] = s.get("child_size", 0)

    # 面包屑（带环检测）
    breadcrumb = []
    if parent_id and not in_trash:
        try:
            pid = _uuid.UUID(parent_id)
        except ValueError:
            pid = None
        seen: set[_uuid.UUID] = set()
        while pid and pid not in seen:
            seen.add(pid)
            r = await db.execute(select(UserFile).where(UserFile.id == pid))
            f = r.scalar()
            if not f:
                break
            breadcrumb.insert(0, {"id": str(f.id), "name": f.filename})
            pid = f.parent_id
    breadcrumb.insert(0, {"id": None, "name": "根目录"})

    return {"items": items, "total": total, "breadcrumb": breadcrumb, "page": page, "size": size}


@router.get("/tree")
async def folder_tree(
    department: str | None = Query(None),
    my: bool = Query(False),
    user_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文件夹树：公盘按部门（scope != private），私盘按用户。"""
    q = select(UserFile).where(
        UserFile.is_folder == True,
        UserFile.is_deleted == False,
        UserFile.in_trash == False,
    )
    if my:
        q = q.where(UserFile.user_id == current_user.id, UserFile.scope == "private")
    elif user_id and current_user.role in ("super_admin", "dept_admin"):
        q = q.where(UserFile.user_id == _parse_uuid(user_id, "用户ID"), UserFile.scope == "private")
    elif department:
        q = q.where(UserFile.scope != "private", UserFile.department == department)
    else:
        q = q.where(UserFile.scope != "private")
    q = _perm_filter(q, current_user)
    rows = (await db.execute(q.order_by(UserFile.parent_id, UserFile.filename))).scalars().all()
    stats = await _folder_agg_stats(db, [r.id for r in rows], current_user)
    by_parent: dict[str | None, list] = {}
    for r in rows:
        by_parent.setdefault(str(r.parent_id) if r.parent_id else None, []).append(
            {"id": str(r.id), "name": r.filename, "scope": r.scope,
             "child_count": stats.get(str(r.id), {}).get("child_count", 0),
             "child_size": stats.get(str(r.id), {}).get("child_size", 0)}
        )

    def build(pid: str | None) -> list:
        return [
            {
                "id": n["id"],
                "name": n["name"],
                "scope": n["scope"],
                "child_count": n["child_count"],
                "child_size": n["child_size"],
                "children": build(n["id"]),
            }
            for n in by_parent.get(pid, [])
        ]

    return build(None)


@router.get("/manifest")
async def folder_manifest(
    folder_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """递归导出文件夹内全部文件清单（相对路径/大小/修改时间），用于完整性核对。"""
    root = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(folder_id, "文件夹ID"),
        UserFile.is_folder == True,
        UserFile.is_deleted == False,
        UserFile.in_trash == False,
    ))).scalar_one_or_none()
    if not root:
        raise HTTPException(404, "文件夹不存在")
    if not _can_read(root, current_user):
        raise HTTPException(403, "无权查看该文件夹")

    dept = current_user.department or ""
    cond_sql = "uf.is_deleted = false AND uf.in_trash = false"
    params: dict = {"root": root.id}
    if current_user.role != "super_admin":
        params["dept"] = dept
        if current_user.role == "dept_admin":
            params["uid"] = str(current_user.id)
            cond_sql += (
                " AND (uf.department = :dept "
                "OR (uf.scope='specific' AND jsonb_exists(uf.visible_departments::jsonb, :dept)) "
                "OR (uf.scope='users' AND uf.visible_user_ids::jsonb ? :uid))"
            )
        elif current_user.role in ("editor", "employee"):
            params["uid"] = str(current_user.id)
            cond_sql += (
                " AND ((uf.department = :dept AND uf.admin_only=false "
                "AND (uf.scope='dept' OR uf.scope='all' "
                "OR (uf.scope='specific' AND jsonb_exists(uf.visible_departments::jsonb, :dept)))) "
                "OR (uf.scope='users' AND uf.visible_user_ids::jsonb ? :uid) "
                "OR (uf.scope='private' AND uf.user_id = :uid::uuid))"
            )
        else:
            params["uid"] = str(current_user.id)
            cond_sql += " AND uf.user_id = :uid::uuid"

    sql = text(f"""
        WITH RECURSIVE tree AS (
            SELECT id, parent_id, filename, file_size, is_folder, created_at, updated_at,
                   ''::text AS rel
            FROM user_files WHERE id = :root
            UNION ALL
            SELECT uf.id, uf.parent_id, uf.filename, uf.file_size, uf.is_folder,
                   uf.created_at, uf.updated_at,
                   CASE WHEN tree.rel = '' THEN uf.filename ELSE tree.rel || '/' || uf.filename END
            FROM user_files uf
            JOIN tree ON uf.parent_id = tree.id
            WHERE {cond_sql}
        )
        SELECT rel, file_size, updated_at FROM tree
        WHERE is_folder = false
        ORDER BY rel
    """)
    rows = (await db.execute(sql, params)).all()
    return {
        "folder": root.filename,
        "folder_id": str(root.id),
        "count": len(rows),
        "total_size": sum(int(r[1] or 0) for r in rows),
        "files": [
            {"path": r[0], "size": int(r[1] or 0),
             "updated_at": r[2].isoformat() if r[2] else None}
            for r in rows
        ],
    }


@router.get("/uploaders")
async def list_uploaders(
    department: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按部门聚合统计上传者文件数（避免分页截断导致计数不准）"""
    q = (
        select(
            UserFile.user_id,
            func.count(UserFile.id).label("count"),
        )
        .where(
            UserFile.is_deleted == False,
            UserFile.in_trash == False,
            UserFile.is_folder == False,
            UserFile.scope == "dept",
        )
        .group_by(UserFile.user_id)
        .order_by(func.count(UserFile.id).desc())
    )
    if department:
        q = q.where(UserFile.department == department)
    q = _perm_filter(q, current_user)
    rows = (await db.execute(q)).all()
    if not rows:
        return {"items": []}
    uids = [r[0] for r in rows]
    ur = await db.execute(select(User).where(User.id.in_(uids)))
    name_map = {u.id: u.display_name for u in ur.scalars().all()}
    return {"items": [
        {"user_id": str(uid), "name": name_map.get(uid, ""), "count": cnt}
        for uid, cnt in rows
    ]}


@router.get("/dept-users")
async def list_dept_users(
    department: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部门成员列表（含各自私盘文件数），供部门主管/超管查看下属个人盘"""
    if current_user.role not in ("super_admin", "dept_admin"):
        raise HTTPException(403, "仅管理员可查看部门成员")
    dept = department or current_user.department or ""
    if current_user.role == "dept_admin" and dept != current_user.department:
        raise HTTPException(403, "无权查看其他部门")
    users = (await db.execute(
        select(User).where(User.department == dept, User.is_active == True)
        .order_by(User.display_name)
    )).scalars().all()
    if not users:
        return {"items": []}
    # 同名双账号（u#### 与拼音）去重：优先保留拼音账号
    seen: dict[str, tuple[int, User]] = {}
    for u in users:
        pref = 0 if re.match(r"^u\d+$", u.username) else 1
        key = u.display_name
        if key not in seen or pref > seen[key][0]:
            seen[key] = (pref, u)
    users = [v[1] for v in seen.values()]
    uids = [u.id for u in users]
    cnt_rows = (await db.execute(
        select(UserFile.user_id, func.count(UserFile.id))
        .where(
            UserFile.user_id.in_(uids),
            UserFile.scope == "private",
            UserFile.is_deleted == False,
            UserFile.in_trash == False,
            UserFile.is_folder == False,
        )
        .group_by(UserFile.user_id)
    )).all()
    cnt_map = {r[0]: r[1] for r in cnt_rows}
    return {"items": [
        {"user_id": str(u.id), "name": u.display_name, "count": cnt_map.get(u.id, 0)}
        for u in users
    ]}


@router.get("/users-tree")
async def users_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全员人员树（按部门分组），供上传可见范围“指定人员”选择。"""
    users = (await db.execute(
        select(User)
        .where(User.is_active == True)
        .order_by(User.department, User.display_name)
    )).scalars().all()
    groups: dict[str, list] = {}
    for u in users:
        groups.setdefault(u.department or "未分组", []).append(
            {"user_id": str(u.id), "name": u.display_name}
        )
    return {"items": [
        {"department": d, "users": us}
        for d, us in sorted(groups.items(), key=lambda x: x[0])
    ]}


class TransferSend(BaseModel):
    file_ids: list[str] = []
    file_id: str | None = None  # 兼容单文件旧调用
    to_user_id: str
    message: str = ""


class VerifyBody(BaseModel):
    parent_id: str | None = None
    expected: list[dict] = []  # [{"name": "xxx.pdf", "size": 12345}]


_TYPE_EXTS = {
    "doc": {"pdf", "doc", "docx", "txt", "md", "ppt", "pptx", "odt", "epub"},
    "sheet": {"xls", "xlsx", "csv", "ods"},
    "image": {"jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tif", "tiff"},
    "video": {"mp4", "webm", "m4v", "mov", "avi", "wmv", "mkv"},
    "audio": {"mp3", "wav", "m4a", "aac", "flac", "ogg"},
}


async def _collect_descendant_files(db: AsyncSession, folder_id, out: list[UserFile]) -> None:
    """递归收集文件夹下的所有文件（用于发送文件夹）。"""
    children = (await db.execute(
        select(UserFile).where(
            UserFile.parent_id == folder_id,
            UserFile.is_deleted == False,
            UserFile.in_trash == False,
        )
    )).scalars().all()
    for ch in children:
        if ch.is_folder:
            await _collect_descendant_files(db, ch.id, out)
        else:
            out.append(ch)


@router.post("/transfers/send")
async def transfer_send(
    body: TransferSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量发送文件/文件夹给指定人员（文件夹自动展开为内部文件，对方接收后进入其私盘）。"""
    raw_ids = list(body.file_ids or [])
    if body.file_id and not raw_ids:
        raw_ids = [body.file_id]
    if not raw_ids:
        raise HTTPException(400, "请选择要发送的文件")
    if len(raw_ids) > 200:
        raise HTTPException(400, "单次最多发送 200 个文件")

    files: list[UserFile] = []
    seen: set = set()
    for raw in raw_ids:
        f = (await db.execute(select(UserFile).where(
            UserFile.id == _parse_uuid(raw, "文件ID"),
            UserFile.is_deleted == False,
            UserFile.in_trash == False,
        ))).scalar_one_or_none()
        if not f:
            raise HTTPException(404, "文件不存在")
        if f.id in seen:
            continue
        seen.add(f.id)
        if f.is_folder:
            await _collect_descendant_files(db, f.id, files)
        else:
            files.append(f)
    files = list({f.id: f for f in files}.values())
    if not files:
        raise HTTPException(400, "所选内容中没有可发送的文件")

    to_user = (await db.execute(select(User).where(
        User.id == _parse_uuid(body.to_user_id, "接收人ID"),
        User.is_active == True,
    ))).scalar_one_or_none()
    if not to_user:
        raise HTTPException(404, "接收人不存在")
    if current_user.id == to_user.id:
        raise HTTPException(400, "不能发送给自己")

    sent_ids: list[str] = []
    for f in files:
        if not _can_read(f, current_user):
            raise HTTPException(403, f"无权发送文件：{f.filename}")
        t = _uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO file_transfers (id, from_user_id, from_name, to_user_id, to_name, "
                "file_id, filename, file_size, message, status, created_at) "
                "VALUES (:id, :fu, :fn, :tu, :tn, :fid, :fl, :fs, :msg, 'pending', now())"
            ),
            {
                "id": t, "fu": current_user.id, "fn": current_user.display_name,
                "tu": to_user.id, "tn": to_user.display_name,
                "fid": f.id, "fl": f.filename, "fs": f.file_size,
                "msg": (body.message or "")[:1000],
            },
        )
        sent_ids.append(str(t))
    await db.commit()
    return {"ids": sent_ids, "count": len(sent_ids), "status": "pending"}


@router.get("/transfers/incoming")
async def transfer_incoming(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        text(
            "SELECT id, from_user_id, from_name, to_name, file_id, filename, file_size, "
            "message, status, created_at, responded_at FROM file_transfers "
            "WHERE to_user_id = :uid AND status = 'pending' ORDER BY created_at DESC"
        ),
        {"uid": current_user.id},
    )).all()
    return {"items": [
        {
            "id": str(r[0]), "from_user_id": str(r[1]), "from_name": r[2],
            "to_name": r[3], "file_id": str(r[4]), "filename": r[5],
            "file_size": int(r[6] or 0), "message": r[7] or "", "status": r[8],
            "created_at": r[9].isoformat() if r[9] else None,
            "responded_at": r[10].isoformat() if r[10] else None,
        }
        for r in rows
    ]}


@router.post("/transfers/{transfer_id}/accept")
async def transfer_accept(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (await db.execute(
        text("SELECT * FROM file_transfers WHERE id = :id"), {"id": _parse_uuid(transfer_id, "传输ID")}
    )).mappings().first()
    if not row or row["to_user_id"] != current_user.id:
        raise HTTPException(404, "传输记录不存在")
    if row["status"] != "pending":
        raise HTTPException(400, "该传输已处理")
    src = (await db.execute(select(UserFile).where(
        UserFile.id == row["file_id"], UserFile.is_deleted == False,
    ))).scalar_one_or_none()
    if not src:
        raise HTTPException(404, "源文件不存在")
    ext = (src.filename or "").rsplit(".", 1)[-1].lower() if "." in (src.filename or "") else ""
    obj_key = f"userfiles/{current_user.id}/{_uuid.uuid4().hex}.{ext}"
    s3 = get_minio_client()
    try:
        obj = await _run_in_thread(s3.get_object, Bucket=settings.MINIO_BUCKET, Key=src.file_path)
        data = obj["Body"].read()
        await _run_in_thread(
            s3.put_object,
            Bucket=settings.MINIO_BUCKET, Key=obj_key, Body=data,
            ContentType=src.mime_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(502, f"文件复制失败：{exc}") from exc
    new_file = UserFile(
        user_id=current_user.id, filename=src.filename,
        original_filename=src.original_filename or src.filename,
        file_size=src.file_size, file_ext=ext,
        mime_type=src.mime_type or "", file_path=obj_key,
        department=current_user.department or "", scope="private",
        employee_download=True, parent_id=None,
    )
    db.add(new_file)
    await db.execute(
        text("UPDATE file_transfers SET status='accepted', responded_at=now() WHERE id=:id"),
        {"id": row["id"]},
    )
    await db.commit()
    await db.refresh(new_file)
    await _log_op(current_user, "transfer_accept", new_file.filename, new_file.id)
    return {"id": str(new_file.id), "filename": new_file.filename, "status": "accepted"}


@router.post("/transfers/{transfer_id}/reject")
async def transfer_reject(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (await db.execute(
        text("SELECT * FROM file_transfers WHERE id = :id"), {"id": _parse_uuid(transfer_id, "传输ID")}
    )).mappings().first()
    if not row or row["to_user_id"] != current_user.id:
        raise HTTPException(404, "传输记录不存在")
    if row["status"] != "pending":
        raise HTTPException(400, "该传输已处理")
    await db.execute(
        text("UPDATE file_transfers SET status='rejected', responded_at=now() WHERE id=:id"),
        {"id": row["id"]},
    )
    await db.commit()
    return {"status": "rejected"}


@router.get("/transfers/sent")
async def transfer_sent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我发出的传输记录（含状态，可撤回未接收的）。"""
    rows = (await db.execute(
        text(
            "SELECT id, to_user_id, to_name, file_id, filename, file_size, "
            "message, status, created_at, responded_at FROM file_transfers "
            "WHERE from_user_id = :uid ORDER BY created_at DESC LIMIT 200"
        ),
        {"uid": current_user.id},
    )).all()
    return {"items": [
        {
            "id": str(r[0]), "to_user_id": str(r[1]), "to_name": r[2],
            "file_id": str(r[3]), "filename": r[4],
            "file_size": int(r[5] or 0), "message": r[6] or "",
            "status": r[7], "created_at": r[8].isoformat() if r[8] else None,
            "responded_at": r[9].isoformat() if r[9] else None,
        }
        for r in rows
    ]}


@router.post("/transfers/{transfer_id}/revoke")
async def transfer_revoke(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤回未接收的传输（仅发送方可操作）。"""
    row = (await db.execute(
        text("SELECT * FROM file_transfers WHERE id = :id"), {"id": _parse_uuid(transfer_id, "传输ID")}
    )).mappings().first()
    if not row or row["from_user_id"] != current_user.id:
        raise HTTPException(404, "传输记录不存在")
    if row["status"] != "pending":
        raise HTTPException(400, "对方已处理，无法撤回")
    await db.execute(
        text("UPDATE file_transfers SET status='revoked', responded_at=now() WHERE id=:id"),
        {"id": row["id"]},
    )
    await db.commit()
    return {"status": "revoked"}


@router.post("/{file_id}/star")
async def star_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """星标/收藏文件（个人维度）。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False,
        UserFile.in_trash == False,
    ))).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问该文件")
    await db.execute(
        text(
            "INSERT INTO file_stars (file_id, user_id, created_at) "
            "VALUES (:fid, :uid, now()) ON CONFLICT DO NOTHING"
        ),
        {"fid": f.id, "uid": current_user.id},
    )
    await db.commit()
    return {"ok": True, "starred": True}


@router.delete("/{file_id}/star")
async def unstar_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消星标。"""
    await db.execute(
        text("DELETE FROM file_stars WHERE file_id = :fid AND user_id = :uid"),
        {"fid": _parse_uuid(file_id, "文件ID"), "uid": current_user.id},
    )
    await db.commit()
    return {"ok": True, "starred": False}


@router.get("/stars")
async def list_stars(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我的星标文件列表（可见范围内）。"""
    rows = (await db.execute(
        text(
            "SELECT uf.* FROM file_stars fs "
            "JOIN user_files uf ON uf.id = fs.file_id "
            "WHERE fs.user_id = :uid AND uf.is_deleted = false AND uf.in_trash = false "
            "ORDER BY fs.created_at DESC LIMIT 500"
        ),
        {"uid": current_user.id},
    )).mappings().all()
    files = [UserFile(**{k: v for k, v in r.items() if k in UserFile.__table__.columns.keys()}) for r in rows]
    files = [f for f in files if _can_read(f, current_user)]
    uids = {f.user_id for f in files}
    uid_map = {}
    if uids:
        ur = await db.execute(select(User).where(User.id.in_(uids)))
        for u in ur.scalars().all():
            uid_map[str(u.id)] = u.display_name
    return {"items": [
        _file_dict(f, uid_map.get(str(f.user_id), ""), _can_write(f, current_user), starred=True)
        for f in files
    ]}


@router.post("/verify")
async def verify_upload(
    body: VerifyBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传完整性对比：按本地清单（文件名+大小）核对服务器目标目录子树。"""
    start_id = _parse_uuid(body.parent_id, "目录ID") if body.parent_id else None
    if start_id is not None:
        folder = (await db.execute(select(UserFile).where(
            UserFile.id == start_id, UserFile.is_folder == True,
            UserFile.is_deleted == False, UserFile.in_trash == False,
        ))).scalar_one_or_none()
        if not folder:
            raise HTTPException(404, "目标目录不存在")
        if not _can_read(folder, current_user):
            raise HTTPException(403, "无权访问该目录")
    # 收集子树文件（递归 CTE）
    cond = "uf.is_deleted = false AND uf.in_trash = false AND uf.is_folder = false"
    if start_id is not None:
        cond += (
            " AND uf.id IN ("
            "  WITH RECURSIVE tree AS ("
            "    SELECT id FROM user_files WHERE id = :root AND is_deleted = false AND in_trash = false"
            "    UNION ALL"
            "    SELECT c.id FROM user_files c JOIN tree t ON c.parent_id = t.id "
            "    WHERE c.is_deleted = false AND c.in_trash = false"
            "  ) SELECT id FROM tree"
            ")"
        )
        rows = (await db.execute(
            text("SELECT filename, file_size FROM user_files uf WHERE " + cond),
            {"root": start_id},
        )).all()
    else:
        rows = (await db.execute(
            text(
                "SELECT filename, file_size FROM user_files uf WHERE "
                "uf.department = :dept AND scope != 'private' AND "
                "uf.is_deleted = false AND uf.in_trash = false AND uf.is_folder = false"
            ),
            {"dept": current_user.department or ""},
        )).all()
    server = {(r[0] or "", int(r[1] or 0)) for r in rows}
    expected = []
    for item in body.expected or []:
        name = str(item.get("name") or "").split("/")[-1]
        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if name:
            expected.append((name, size))
    expected_set = set(expected)
    missing = [{"name": n, "size": s} for n, s in expected if (n, s) not in server]
    extra = [{"name": n, "size": s} for n, s in server if (n, s) not in expected_set]
    return {
        "expected": len(expected),
        "found": len(expected) - len(missing),
        "missing": missing,
        "extra": extra,
        "ok": not missing,
        "message": (
            "全部完整" if not missing and not extra
            else f"少了 {len(missing)} 个" + (f" / 多了 {len(extra)} 个" if extra else "")
        ),
    }


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员仪表盘概览"""
    cache_key = f"{current_user.role}|{current_user.department or ''}"
    now = time.time()
    cached = _OVERVIEW_CACHE.get(cache_key)
    if cached and now - cached[0] < _OVERVIEW_TTL:
        return cached[1]
    is_admin = current_user.role in ("super_admin", "dept_admin")

    # 部门统计
    dept_base = select(
        UserFile.department,
        func.count(UserFile.id).label("count"),
        func.coalesce(func.sum(UserFile.file_size), 0).label("size"),
        func.max(UserFile.updated_at).label("last_active")
    ).where(
        UserFile.is_deleted == False, UserFile.in_trash == False,
        UserFile.is_folder == False, UserFile.department != None,
        UserFile.scope == "dept",
    )
    if not is_admin:
        dept_base = dept_base.where(UserFile.department == (current_user.department or ""))
    else:
        dept_base = dept_base.where(UserFile.department.in_(DEPARTMENTS))
    dept_base = dept_base.group_by(UserFile.department)
    dept_rows = (await db.execute(dept_base)).all()
    dept_map = {r[0]: {"count": r[1], "size": r[2] or 0, "last_active": r[3].isoformat() if r[3] else None} for r in dept_rows}
    # Fill in all departments even if empty, include root folder ID
    all_depts = DEPARTMENTS if is_admin else [current_user.department or ""]
    # Query department root folder IDs (名称与部门一致，避免跨部门同名误配)
    dept_folders_q = select(UserFile.id, UserFile.filename).where(
        UserFile.is_folder == True, UserFile.parent_id == None,
        UserFile.filename.in_(all_depts),
        UserFile.department == UserFile.filename,
        UserFile.scope == "dept",
        UserFile.in_trash == False, UserFile.is_deleted == False,
    )
    dept_folders = {r[1]: str(r[0]) for r in (await db.execute(dept_folders_q)).all()}
    dept_stats = [{"department": d, "folder_id": dept_folders.get(d, ""),
                    "count": dept_map.get(d, {}).get("count", 0),
                    "size": dept_map.get(d, {}).get("size", 0),
                    "last_active": dept_map.get(d, {}).get("last_active")} for d in all_depts]

    # 最近上传
    recent_base = select(UserFile).where(
        UserFile.is_deleted == False, UserFile.in_trash == False,
        UserFile.is_folder == False, UserFile.scope == "dept",
    ).order_by(UserFile.updated_at.desc()).limit(10)
    if not is_admin:
        recent_base = recent_base.where(UserFile.department == (current_user.department or ""))
    recent_rows = (await db.execute(recent_base)).scalars().all()

    # 加载上传者
    uid_map = {}
    uids = list({f.user_id for f in recent_rows})
    if uids:
        ur = await db.execute(select(User).where(User.id.in_(uids)))
        for u in ur.scalars().all():
            uid_map[str(u.id)] = u.display_name

    recent = [{"id": str(f.id), "filename": f.filename, "department": f.department,
               "file_ext": f.file_ext, "file_size": f.file_size,
               "uploader_name": uid_map.get(str(f.user_id), ""),
               "parent_id": str(f.parent_id) if f.parent_id else None,
               "updated_at": f.updated_at.isoformat() if f.updated_at else None}
              for f in recent_rows]

    # 我的文件数、回收站数
    my_q = select(func.count(UserFile.id)).where(
        UserFile.is_deleted == False, UserFile.in_trash == False,
        UserFile.is_folder == False, UserFile.user_id == current_user.id,
        UserFile.scope == "private")
    my_count = (await db.execute(my_q)).scalar() or 0
    my_size = (await db.execute(select(func.coalesce(func.sum(UserFile.file_size), 0)).where(
        UserFile.is_deleted == False, UserFile.in_trash == False,
        UserFile.is_folder == False, UserFile.user_id == current_user.id,
        UserFile.scope == "private"))).scalar() or 0

    trash_q = select(func.count(UserFile.id)).where(
        UserFile.is_deleted == False, UserFile.in_trash == True)
    trash_q = _perm_filter(trash_q, current_user)
    trash_count = (await db.execute(trash_q)).scalar() or 0

    result = {"dept_stats": dept_stats, "recent": recent,
              "my_count": my_count, "my_size": my_size, "trash_count": trash_count}
    _OVERVIEW_CACHE[cache_key] = (time.time(), result)
    return result


@router.get("/stats")
async def storage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """存储统计 + 配额"""
    cache_key = f"{current_user.role}|{current_user.department or ''}"
    now = time.time()
    cached = _STATS_CACHE.get(cache_key)
    if cached and now - cached[0] < _OVERVIEW_TTL:
        return cached[1]
    base = select(func.count(UserFile.id), func.coalesce(func.sum(UserFile.file_size), 0)).where(
        UserFile.is_deleted == False, UserFile.in_trash == False, UserFile.is_folder == False
    )
    base = _perm_filter(base, current_user)
    r = (await db.execute(base)).one()
    total_count, total_size = r[0], r[1] or 0

    # 部门统计（超管看）
    dept_stats = []
    if current_user.role == "super_admin":
        dr = await db.execute(
            select(UserFile.department, func.count(UserFile.id), func.sum(UserFile.file_size))
            .where(UserFile.is_deleted == False, UserFile.in_trash == False,
                   UserFile.is_folder == False, UserFile.scope == "dept")
            .group_by(UserFile.department).order_by(func.sum(UserFile.file_size).desc())
        )
        dept_stats = [{"department": r[0] or "未分配", "count": r[1], "size": r[2] or 0} for r in dr]

    # 回收站计数
    trash_q = select(func.count(UserFile.id)).where(
        UserFile.is_deleted == False, UserFile.in_trash == True)
    trash_q = _perm_filter(trash_q, current_user)
    trash_count = (await db.execute(trash_q)).scalar() or 0

    result = {"total_count": total_count, "total_size": total_size,
              "dept_stats": dept_stats, "trash_count": trash_count,
              "quota": 10 * 1024 * 1024 * 1024}  # 10GB 配额
    _STATS_CACHE[cache_key] = (time.time(), result)
    return result


@router.post("/folders")
async def create_folder(
    body: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建文件夹"""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "文件夹名称不能为空")
    scope = body.scope or "dept"
    if scope not in ("dept", "private"):
        raise HTTPException(400, "无效的文件范围")

    parent_uuid = _parse_uuid(body.parent_id, "父文件夹") if body.parent_id else None
    if parent_uuid:
        p = (await db.execute(select(UserFile).where(
            UserFile.id == parent_uuid, UserFile.is_deleted == False
        ))).scalar()
        if not p or not p.is_folder:
            raise HTTPException(400, "父文件夹不存在")
        if p.in_trash:
            raise HTTPException(400, "父文件夹在回收站中")
        if not _can_upload_into(p, current_user):
            raise HTTPException(403, "无权在该文件夹下创建")
        if scope != p.scope:
            raise HTTPException(400, "文件夹范围与父文件夹不一致")
        dept = p.department or body.department or current_user.department or ""
    else:
        dept = body.department or current_user.department or ""
        # 非管理员只能在本人部门下创建顶层文件夹
        if current_user.role not in ("super_admin", "dept_admin") and dept != (current_user.department or ""):
            raise HTTPException(403, "无权在该部门创建文件夹")
        # 私盘根文件夹：创建者即本人（user_id 固定为当前用户），无需额外限制

    # 同部门、同父目录下同名文件夹幂等返回
    existing = (await db.execute(select(UserFile).where(
        UserFile.is_folder == True, UserFile.filename == name,
        UserFile.parent_id == parent_uuid, UserFile.department == dept,
        UserFile.scope == scope,
        UserFile.in_trash == False, UserFile.is_deleted == False,
    ))).scalar()
    if existing:
        await db.refresh(existing)
        return _file_dict(existing)

    f = UserFile(
        user_id=current_user.id, filename=name, is_folder=True,
        parent_id=parent_uuid,
        department=dept,
        scope=scope,
        original_filename=name,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    await _log_op(current_user, "create_folder", name, f.id)
    return _file_dict(f)


@router.put("/folders/{folder_id}")
async def rename_folder(
    folder_id: str, body: FolderRename = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名文件夹（兼容旧接口）"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(folder_id, "文件夹ID"),
        UserFile.is_folder == True, UserFile.in_trash == False, UserFile.is_deleted == False,
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件夹不存在")
    if not _can_write(f, current_user):
        raise HTTPException(403, "无权操作")
    if not (body.name or "").strip():
        raise HTTPException(400, "名称不能为空")
    old_name = f.filename
    f.filename = body.name.strip()
    await db.commit()
    await db.refresh(f)
    await _log_op(current_user, "rename", f.filename, f.id, detail=f"{old_name} -> {f.filename}")
    return _file_dict(f)


@router.put("/{file_id}")
async def rename_file(
    file_id: str, body: FolderRename = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名文件或文件夹（通用接口）"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.in_trash == False, UserFile.is_deleted == False,
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_write(f, current_user):
        raise HTTPException(403, "无权操作")
    if not (body.name or "").strip():
        raise HTTPException(400, "名称不能为空")
    old_name = f.filename
    f.filename = body.name.strip()
    if body.employee_download is not None:
        f.employee_download = body.employee_download
    await db.commit()
    await db.refresh(f)
    await _log_op(current_user, "rename", f.filename, f.id, detail=f"{old_name} -> {f.filename}")
    return _file_dict(f)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    parent_id: str | None = Form(None),
    scope: str = Form("dept"),
    overwrite: bool = Form(False),
    employee_download: bool = Form(True),
    visible_departments: str | None = Form(None),
    visible_user_ids: str | None = Form(None),
    admin_only: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文件"""
    if not file.filename:
        raise HTTPException(400, "文件名为空")
    if scope not in ("dept", "private", "all", "specific", "users"):
        raise HTTPException(400, "无效的文件范围")
    if scope == "all" and current_user.role != "super_admin":
        raise HTTPException(403, "仅系统管理员可设置全员可见，部门管理员/员工无权将文件开放给全公司")
    vis_depts: list[str] = []
    if visible_departments:
        try:
            parsed = json.loads(visible_departments)
            if not isinstance(parsed, list):
                raise ValueError("not a list")
            vis_depts = [str(d).strip() for d in parsed if str(d).strip()]
        except Exception:
            # 兼容逗号分隔/带引号等非严格 JSON 写法
            vis_depts = [
                d.strip().strip('"').strip("'")
                for d in re.split(r"[,，\s]+", visible_departments.strip("[]").strip('"'))
                if d.strip()
            ]
    if scope == "specific" and not vis_depts:
        raise HTTPException(400, "指定部门可见时需提供可见部门列表")
    vis_user_ids: list[str] = []
    if visible_user_ids:
        try:
            parsed_u = json.loads(visible_user_ids)
            if not isinstance(parsed_u, list):
                raise ValueError("not a list")
            vis_user_ids = [str(x).strip() for x in parsed_u if str(x).strip()]
        except Exception:
            vis_user_ids = [
                x.strip().strip('"').strip("'")
                for x in re.split(r"[,，\s]+", visible_user_ids.strip("[]").strip('"'))
                if x.strip()
            ]
    if scope == "users" and not vis_user_ids:
        raise HTTPException(400, "指定人员可见时需提供可见人员列表")
    if admin_only and scope not in ("dept",):
        raise HTTPException(400, "仅管理员可见仅支持本部门范围")

    # 流式上传：不把整个文件读进内存，直接边读边传（大文件自动走 multipart）
    fobj = file.file
    fobj.seek(0, 2)
    file_size = fobj.tell()
    fobj.seek(0)
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(413, f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)")

    parent_uuid = _parse_uuid(parent_id, "父文件夹") if parent_id else None
    parent = None
    if parent_uuid:
        parent = (await db.execute(select(UserFile).where(
            UserFile.id == parent_uuid, UserFile.is_deleted == False
        ))).scalar()
        if not parent or not parent.is_folder:
            raise HTTPException(400, "父文件夹不存在")
        if parent.in_trash:
            raise HTTPException(400, "父文件夹在回收站中")
        if not _can_upload_into(parent, current_user):
            raise HTTPException(403, "无权在该文件夹下上传")
        # 仅约束公盘/私盘边界；可见范围（本部门/全员/指定部门）允许子级细化
        if (scope == "private") != (parent.scope == "private"):
            raise HTTPException(400, "文件范围与父文件夹不一致")
        if scope == "specific" and parent.scope == "private":
            raise HTTPException(400, "私盘文件夹不支持指定部门可见")
    elif scope in ("dept", "all", "specific"):
        # 公盘上传未指定目录时，自动落到部门公盘根文件夹
        dept_root = (await db.execute(select(UserFile).where(
            UserFile.is_folder == True, UserFile.parent_id == None,
            UserFile.department == (current_user.department or ""),
            UserFile.scope == "dept",
            UserFile.in_trash == False, UserFile.is_deleted == False,
        ).order_by(UserFile.created_at).limit(1))).scalar()
        if dept_root:
            parent_uuid = dept_root.id
            parent = dept_root

    # 私盘配额：每人 10GB（公盘为部门共享，不按个人限额）
    if scope == "private":
        used = (
            await db.execute(
                select(func.coalesce(func.sum(UserFile.file_size), 0)).where(
                    UserFile.user_id == current_user.id,
                    UserFile.scope == "private",
                    UserFile.is_deleted == False,
                    UserFile.in_trash == False,
                    UserFile.is_folder == False,
                )
            )
        ).scalar() or 0
        quota = 10 * 1024 * 1024 * 1024
        if used + file_size > quota:
            raise HTTPException(
                status_code=413,
                detail=f"私盘配额不足（已用 {used / 1024 / 1024 / 1024:.1f}GB / 10GB）",
            )

    # 同名文件检测
    dup = (
        await db.execute(
            select(UserFile)
            .where(
                UserFile.parent_id == parent_uuid,
                UserFile.filename == file.filename,
                UserFile.scope == scope,
                UserFile.is_deleted == False,
                UserFile.in_trash == False,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if dup and not overwrite:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "同名文件已存在",
                "exists": True,
                "id": str(dup.id),
            },
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    obj_key = f"userfiles/{current_user.id}/{_uuid.uuid4().hex}.{ext}"

    s3 = get_minio_client()
    try:
        from boto3.s3.transfer import TransferConfig

        await _run_in_thread(_ensure_bucket_exists, s3)
        cfg = TransferConfig(
            multipart_threshold=16 * 1024 * 1024,
            multipart_chunksize=16 * 1024 * 1024,
            max_concurrency=4,
            use_threads=True,
        )
        await _run_in_thread(
            s3.upload_fileobj, fobj, settings.MINIO_BUCKET, obj_key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
            Config=cfg,
        )
    except Exception as e:
        logger.error("MinIO upload failed: %s", e, exc_info=True)
        raise HTTPException(500, f"存储失败: {e}")

    if dup and overwrite:
        old_path = dup.file_path
        dup.file_path = obj_key
        dup.file_size = file_size
        dup.mime_type = file.content_type or ""
        dup.original_filename = file.filename
        dup.employee_download = employee_download
        try:
            await db.commit()
        except Exception:
            try:
                await _run_in_thread(s3.delete_object, Bucket=settings.MINIO_BUCKET, Key=obj_key)
            except Exception:
                pass
            raise HTTPException(500, "保存文件记录失败")
        if old_path:
            try:
                old_bucket, old_key = old_path[5:].split("/", 1)
                await _run_in_thread(s3.delete_object, Bucket=old_bucket, Key=old_key)
            except Exception:
                pass
        await _log_op(current_user, "upload_overwrite", dup.filename, dup.id)
        return {"id": str(dup.id), "overwritten": True}

    f = UserFile(
        user_id=current_user.id, filename=file.filename,
        original_filename=file.filename, file_size=file_size,
        file_ext=ext, mime_type=file.content_type or "", file_path=obj_key,
        # 文件部门跟随父文件夹，避免跨部门上传后数据不一致
        department=(parent.department if parent else current_user.department or ""),
        parent_id=parent_uuid,
        scope=scope,
        visible_departments=vis_depts or None,
        visible_user_ids=vis_user_ids or None,
        admin_only=admin_only,
        employee_download=employee_download,
    )
    db.add(f)
    try:
        await db.commit()
    except Exception:
        # 数据库写入失败时回滚已上传的对象，避免孤儿文件
        try:
            await _run_in_thread(s3.delete_object, Bucket=settings.MINIO_BUCKET, Key=obj_key)
        except Exception:
            pass
        raise HTTPException(500, "保存文件记录失败")
    await db.refresh(f)
    await _log_op(current_user, "upload", f.filename, f.id)
    return _file_dict(f)


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    inline: bool = Query(False),
    token: str = Query("", description="Short-lived download token for browser navigation"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """下载文件"""
    if token and not current_user:
        try:
            payload = decode_token(token)
            if payload.get("scope") != "download" or payload.get("file") != file_id:
                raise HTTPException(status_code=403, detail="下载令牌与文件不匹配")
            current_user = await db.get(User, payload.get("sub"))
            if not current_user or not current_user.is_active:
                raise HTTPException(status_code=403, detail="用户不存在或已停用")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="无效的下载令牌")
    if not current_user:
        raise HTTPException(status_code=401, detail="需要登录")

    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")
    if not _can_download(f, current_user):
        raise HTTPException(403, "该文件未开放给员工下载")
    try:
        from fastapi.responses import StreamingResponse
        from urllib.parse import quote
        obj = get_minio_client().get_object(Bucket=settings.MINIO_BUCKET, Key=f.file_path)
        safe_name = quote(f.filename)
        disp = "inline" if inline else "attachment"
        return StreamingResponse(
            obj['Body'].iter_chunks(chunk_size=65536),
            media_type=f.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f"{disp}; filename*=UTF-8''{safe_name}",
                     "Content-Length": str(f.file_size)})
    except Exception as e:
        logger.error("Download failed: %s", e, exc_info=True)
        raise HTTPException(500, f"下载失败: {e}")


@router.get("/{file_id}/download-token")
async def get_download_token(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成短时下载令牌（浏览器导航下载时无法携带 Authorization 头）。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(status_code=403, detail="无权访问")
    if not _can_download(f, current_user):
        raise HTTPException(status_code=403, detail="该文件未开放给员工下载")
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    from jose import jwt
    token = jwt.encode(
        {
            "sub": str(current_user.id),
            "file": file_id,
            "exp": expire,
            "scope": "download",
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"token": token}


@router.post("/batch/download")
async def batch_download(
    body: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量下载：选中的文件 + 文件夹内所有文件打包为 zip。"""
    ids = _parse_uuid_list(body.ids)
    if not ids:
        raise HTTPException(status_code=400, detail="请选择文件")
    rows = (
        await db.execute(
            select(UserFile).where(
                UserFile.id.in_(ids), UserFile.is_deleted == False
            )
        )
    ).scalars().all()
    files_to_zip: list[UserFile] = []
    seen: set = set()
    for f in rows:
        if not _can_read(f, current_user):
            continue
        if not _can_download(f, current_user):
            continue
        if f.is_folder:
            desc_ids = await _collect_descendant_ids(db, [f.id])
            desc = await _fetch_rows_by_ids(db, desc_ids)
            for x in desc:
                if not x.is_folder and _can_read(x, current_user) and _can_download(x, current_user) and x.id not in seen:
                    seen.add(x.id)
                    files_to_zip.append(x)
        else:
            if f.id not in seen:
                seen.add(f.id)
                files_to_zip.append(f)
    if not files_to_zip:
        raise HTTPException(status_code=403, detail="没有可下载的文件")

    import os
    import tempfile
    import zipfile
    from starlette.background import BackgroundTask
    from fastapi.responses import FileResponse

    fd, tmp = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    s3 = get_minio_client()
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files_to_zip:
                try:
                    obj = s3.get_object(Bucket=settings.MINIO_BUCKET, Key=f.file_path)
                    zf.writestr(f.filename, obj["Body"].read())
                except Exception:
                    continue
    except Exception as exc:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"打包失败: {exc}")

    def cleanup():
        try:
            os.unlink(tmp)
        except Exception:
            pass

    return FileResponse(
        tmp,
        media_type="application/zip",
        filename="批量下载.zip",
        background=BackgroundTask(cleanup),
    )


@router.get("/{file_id}/preview-token")
async def get_file_preview_token(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成短时单文件预览 token，供 iframe 直连（iframe 无法带请求头）。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")

    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": str(current_user.id),
        "file": file_id,
        "exp": expire,
        "scope": "preview",
    }
    from jose import jwt
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token}


@router.get("/{file_id}/raw")
async def raw_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回文本类文件原文（md/txt/csv 等），供前端渲染。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")
    if f.file_size and f.file_size > 5 * 1024 * 1024:
        raise HTTPException(413, "文件过大，无法在线预览")
    s3 = get_minio_client()
    obj = await _run_in_thread(s3.get_object, Bucket=settings.MINIO_BUCKET, Key=f.file_path)
    content = await _run_in_thread(lambda: obj["Body"].read())
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    token: str = Query("", description="iframe 预览 token（或完整 JWT）"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """公盘预览：PDF 直出、Office 后台转换（202 轮询）、其余类型给预签名 URL。"""
    if token:
        try:
            payload = decode_token(token)
        except HTTPException:
            raise HTTPException(status_code=401, detail="无效的预览令牌")
        if payload.get("scope") == "preview":
            if payload.get("file") != file_id:
                raise HTTPException(status_code=403, detail="预览令牌与文件不匹配")
        user = await db.get(User, payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="用户不存在或已停用")
        current_user = user
    if not current_user:
        raise HTTPException(status_code=401, detail="需要登录")

    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")

    from urllib.parse import quote

    def _pdf_response(content: bytes) -> Response:
        safe_name = quote(f.filename) + ".pdf"
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}"},
        )

    ext = f.file_ext.lower()
    if ext == "pdf":
        s3 = get_minio_client()
        content = await _run_in_thread(lambda: _read_minio_object(s3, f.file_path))
        if content:
            return _pdf_response(content)
        raise HTTPException(status_code=502, detail="预览生成失败，请下载查看")

    if ext in OFFICE_PREVIEW_EXTS:
        s3 = get_minio_client()
        cache_key = f"previews/userfiles/{f.id}.pdf"
        cached = await _run_in_thread(lambda: _read_minio_object(s3, cache_key))
        if cached:
            return _pdf_response(cached)

        last_fail = _CONVERT_FAILED_FILES.get(str(f.id), 0)
        if last_fail and time.time() - last_fail < _CONVERT_FAIL_TTL:
            raise HTTPException(status_code=502, detail="该文件暂时无法生成预览，请点击下载查看")

        if str(f.id) not in _CONVERTING_FILES:
            _CONVERTING_FILES[str(f.id)] = time.time()
            task = asyncio.create_task(_convert_and_cache_file(str(f.id)))
            _CONVERT_TASKS_FILES.add(task)
            task.add_done_callback(_CONVERT_TASKS_FILES.discard)
        return JSONResponse(status_code=202, content={"status": "converting"})

    # 其余类型：预签名 URL（图片/视频等由前端播放）
    s3 = _get_presigned_client()
    url = await _run_in_thread(
        s3.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": f.file_path},
        ExpiresIn=settings.MINIO_PRESIGNED_EXPIRES,
    )
    return {"preview_url": url, "converted": False}


@router.get("/{file_id}/onlyoffice-config")
async def file_onlyoffice_config(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """公盘 Office 文件 OnlyOffice 预览配置（只读）。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")
    ext = (f.file_ext or "").lower()
    support = {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "txt", "csv", "md"}
    if ext not in support:
        raise HTTPException(400, "该格式不支持在线预览")
    if not settings.ONLYOFFICE_URL or not settings.ONLYOFFICE_JWT_SECRET:
        raise HTTPException(503, "OnlyOffice 未配置")
    doc_type = {"doc": "word", "docx": "word", "odt": "word", "txt": "word",
                "xls": "cell", "xlsx": "cell", "ods": "cell", "csv": "cell",
                "ppt": "slide", "pptx": "slide", "odp": "slide", "md": "word"}[ext]
    import hashlib
    doc_url = f"{settings.ONLYOFFICE_INTERNAL_BASE}/api/onlyoffice/source/{make_source_token('file', str(f.id))}"
    key = hashlib.sha256(f"{f.id}:{f.updated_at}:{f.file_size}".encode()).hexdigest()[:40]
    config = {
        "document": {
            "fileType": "txt" if ext == "md" else ext, "key": key, "title": f.filename, "url": doc_url,
            "permissions": {"edit": False, "download": True, "print": True, "review": False, "comment": False},
        },
        "documentType": doc_type,
        "editorConfig": {
            "mode": "view", "lang": "zh-CN",
            "user": {"id": str(current_user.id), "name": current_user.display_name or current_user.username},
            "customization": {"autosave": False, "chat": False, "comments": False, "compactHeader": True,
                              "compactToolbar": True, "hideRightMenu": True, "help": False, "plugins": False,
                              "showReviewChanges": False, "spellcheck": False, "toolbarHideFileName": False},
        },
    }
    from jose import jwt
    token = jwt.encode(config, settings.ONLYOFFICE_JWT_SECRET, algorithm="HS256")
    return {"documentServerUrl": settings.ONLYOFFICE_URL.rstrip("/"), "config": config, "token": token}


@router.post("/{file_id}/share")
async def create_share_link(
    file_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成带有效期的公盘分享链接。"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False, UserFile.is_folder == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    if not _can_read(f, current_user):
        raise HTTPException(403, "无权访问")
    if not _can_download(f, current_user):
        raise HTTPException(403, "该文件未开放给员工下载")
    days = max(1, min(int(body.get("expire_days", 7)), 30))
    import secrets
    token = secrets.token_urlsafe(24)
    from datetime import timedelta
    await db.execute(
        text(
            "INSERT INTO user_file_shares (user_file_id, token, expire_at, created_by) "
            "VALUES (:fid, :tok, :exp, :uid)"
        ),
        {
            "fid": f.id,
            "tok": token,
            "exp": datetime.now(timezone.utc) + timedelta(days=days),
            "uid": current_user.id,
        },
    )
    await db.commit()
    return {"token": token, "url": f"/api/files/share/{token}/download", "expire_days": days}


@router.get("/share/{token}/download")
async def share_download(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """公开分享下载（无需登录，受有效期限制）。"""
    row = (
        await db.execute(
            text("SELECT user_file_id, expire_at, download_count FROM user_file_shares WHERE token = :t"),
            {"t": token},
        )
    ).first()
    if not row:
        raise HTTPException(404, "链接不存在或已失效")
    if row[1] and row[1] < datetime.now(timezone.utc):
        raise HTTPException(410, "链接已过期")
    f = (await db.execute(select(UserFile).where(
        UserFile.id == row[0], UserFile.is_deleted == False, UserFile.in_trash == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "文件不存在")
    await db.execute(
        text("UPDATE user_file_shares SET download_count = download_count + 1 WHERE token = :t"),
        {"t": token},
    )
    await db.commit()
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote
    obj = get_minio_client().get_object(Bucket=settings.MINIO_BUCKET, Key=f.file_path)
    safe_name = quote(f.filename)
    return StreamingResponse(
        obj["Body"].iter_chunks(chunk_size=65536),
        media_type=f.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
                 "Content-Length": str(f.file_size)},
    )


@router.post("/batch/trash")
async def batch_trash(
    body: BatchDelete, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量移到回收站（文件夹级联）"""
    ids = _parse_uuid_list(body.ids)
    if not ids:
        return {"ok": True, "trashed": 0}
    result = await db.execute(select(UserFile).where(
        UserFile.id.in_(ids), UserFile.is_deleted == False
    ))
    allowed = [f for f in result.scalars().all() if _can_write(f, current_user)]
    if not allowed:
        return {"ok": True, "trashed": 0}

    trashed = await _update_descendants(db, [f.id for f in allowed], in_trash=True)
    await db.commit()
    await _log_op(
        current_user, "batch_trash",
        ",".join(x.filename for x in allowed[:20]),
        detail=f"trashed={trashed}",
    )
    return {"ok": True, "trashed": trashed}


@router.post("/batch/restore")
async def batch_restore(
    body: BatchDelete, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量恢复（含被级联回收的子项，以及仍在回收站中的上级目录）"""
    ids = _parse_uuid_list(body.ids)
    if not ids:
        return {"ok": True}
    result = await db.execute(select(UserFile).where(
        UserFile.id.in_(ids), UserFile.is_deleted == False
    ))
    allowed = [f for f in result.scalars().all() if _can_write(f, current_user)]
    if not allowed:
        return {"ok": True}

    restore_ids: set[_uuid.UUID] = {f.id for f in allowed}
    # 级联恢复所有在回收站中的子项
    desc_ids = await _collect_descendant_ids(db, list(restore_ids))
    restore_ids.update(desc_ids)
    # 上级目录若也在回收站，一并恢复（避免子项恢复后仍藏在不可见目录下）
    pending = list(allowed)
    seen: set[_uuid.UUID] = set(restore_ids)
    while pending:
        cur = pending.pop()
        if cur.parent_id and cur.parent_id not in seen:
            p = (await db.execute(select(UserFile).where(
                UserFile.id == cur.parent_id, UserFile.is_deleted == False
            ))).scalar()
            if p and p.in_trash:
                seen.add(p.id)
                restore_ids.add(p.id)
                pending.append(p)

    restored = await _update_descendants(db, list(restore_ids), in_trash=False)
    await db.commit()
    await _log_op(
        current_user, "batch_restore",
        ",".join(x.filename for x in allowed[:20]),
        detail=f"restored={restored}",
    )
    return {"ok": True, "restored": restored}


@router.post("/batch/move")
async def batch_move(
    body: BatchMove, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量移动（校验目标文件夹，防环）"""
    ids = _parse_uuid_list(body.ids)
    if not ids:
        return {"ok": True}

    target = _parse_uuid(body.target_folder_id, "目标文件夹") if body.target_folder_id else None
    if target:
        t = (await db.execute(select(UserFile).where(
            UserFile.id == target, UserFile.is_deleted == False
        ))).scalar()
        if not t or not t.is_folder:
            raise HTTPException(400, "目标文件夹不存在")
        if t.in_trash:
            raise HTTPException(400, "目标文件夹在回收站中")
        if not _can_write(t, current_user):
            raise HTTPException(403, "无权移动到该文件夹")

    result = await db.execute(select(UserFile).where(
        UserFile.id.in_(ids), UserFile.is_deleted == False
    ))
    moved = 0
    for f in result.scalars().all():
        if not _can_write(f, current_user):
            continue
        if f.id == target:
            continue  # 移到自身，忽略
        if f.is_folder and target:
            if await _is_descendant(db, target, f.id):
                raise HTTPException(400, "不能移动到自身或其子文件夹中")
        f.parent_id = target
        moved += 1
    await db.commit()
    await _log_op(
        current_user, "move",
        ",".join(str(x) for x in ids[:20]),
        detail=f"target={body.target_folder_id or 'root'}, moved={moved}",
    )
    return {"ok": True, "moved": moved}


@router.delete("/batch/permanent")
async def batch_delete_permanent(
    body: BatchDelete, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """永久删除（需超管）：同时删除 MinIO 对象与子项"""
    if current_user.role != "super_admin":
        raise HTTPException(403, "仅管理员可永久删除")
    ids = _parse_uuid_list(body.ids)
    if not ids:
        return {"ok": True, "deleted": 0}

    result = await db.execute(select(UserFile).where(
        UserFile.id.in_(ids), UserFile.is_deleted == False
    ))
    roots = list(result.scalars().all())
    all_ids = await _collect_descendant_ids(db, [f.id for f in roots])
    all_rows = await _fetch_rows_by_ids(db, all_ids)
    await _delete_minio_objects(all_rows)
    deleted = await _update_descendants(db, [f.id for f in roots], is_deleted=True)
    await db.commit()
    await _log_op(
        current_user, "permanent_delete",
        ",".join(x.filename for x in roots[:20]),
        detail=f"deleted={deleted}",
    )
    return {"ok": True, "deleted": deleted}


@router.delete("/batch/empty-trash")
async def empty_trash(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空回收站（超管全量，部门管理员仅本部门范围）"""
    if current_user.role not in ("super_admin", "dept_admin"):
        raise HTTPException(403, "仅管理员可清空回收站")
    base = select(UserFile).where(
        UserFile.is_deleted == False, UserFile.in_trash == True
    )
    base = _perm_filter(base, current_user)
    # 轻量取待删对象路径（避免把几十万 ORM 对象加载进内存）
    keys_q = select(UserFile.file_path).where(
        UserFile.is_deleted == False, UserFile.in_trash == True
    )
    keys_q = _perm_filter(keys_q, current_user)
    keys = [k for k in (await db.execute(keys_q)).scalars().all() if k]
    # 数据库一次性批量标记删除（快），MinIO 对象转入后台异步清理
    stmt = (
        update(UserFile)
        .where(UserFile.is_deleted == False, UserFile.in_trash == True)
        .values(is_deleted=True)
    )
    stmt = _perm_filter(stmt, current_user)
    res = await db.execute(stmt)
    await db.commit()
    deleted = res.rowcount or 0
    if keys:
        task = asyncio.create_task(_delete_minio_keys(keys))
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
    await _log_op(current_user, "empty_trash", detail=f"deleted={deleted}, minio_keys={len(keys)}")
    return {"ok": True, "deleted": deleted, "minio_keys": len(keys), "cleanup_async": True}


@router.delete("/{file_id}")
async def delete_single(
    file_id: str, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移到回收站（文件夹级联）"""
    f = (await db.execute(select(UserFile).where(
        UserFile.id == _parse_uuid(file_id, "文件ID"),
        UserFile.is_deleted == False
    ))).scalar()
    if not f:
        raise HTTPException(404, "不存在")
    if not _can_write(f, current_user):
        raise HTTPException(403, "无权操作")

    trashed = await _update_descendants(db, [f.id], in_trash=True)
    await db.commit()
    await _log_op(current_user, "delete", f.filename, f.id, detail=f"trashed={trashed}")
    return {"ok": True, "trashed": trashed}


@router.post("/init-dept-folders")
async def init_dept_folders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """初始化部门顶层文件夹（幂等）"""
    if current_user.role != "super_admin":
        raise HTTPException(403, "仅管理员")
    created = []
    for dept in DEPARTMENTS:
        existing = (await db.execute(select(UserFile).where(
            UserFile.is_folder == True, UserFile.parent_id == None,
            UserFile.filename == dept, UserFile.department == dept,
            UserFile.scope == "dept",
            UserFile.in_trash == False, UserFile.is_deleted == False,
        ))).scalar()
        if not existing:
            f = UserFile(
                user_id=current_user.id, filename=dept, is_folder=True,
                parent_id=None, department=dept, scope="dept", original_filename=dept,
            )
            db.add(f)
            created.append(dept)
    await db.commit()
    return {"ok": True, "departments": DEPARTMENTS, "created": created}
