import logging
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.auth import get_current_user_optional
from app.permissions import PermissionService
from app.api import auth, categories, documents, search, personal, admin, system, cosmetics, device_reg, files, ai, ops, oo_source, announcements
from app.middleware.error_handler import global_exception_handler
from app.middleware.logging import request_logging_middleware
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.services.search_service import _get_search_client_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_logging_middleware)

# ── Chrome 142+ Local Network Access fix (dev only) ─────
if settings.ENVIRONMENT == "development":
    @app.middleware("http")
    async def add_private_network_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(categories.router, prefix="/api/categories", tags=["分类"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])
app.include_router(personal.router, prefix="/api/me", tags=["个人中心"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
app.include_router(files.router, prefix="/api/files", tags=["文件存储"])
app.include_router(system.router, prefix="/api/admin", tags=["系统设置"])
app.include_router(cosmetics.router, tags=["化妆品原料搜索"])
app.include_router(device_reg.router, tags=["器械注册"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI 接口"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["更新公告"])
app.include_router(ops.router, prefix="/api/admin", tags=["运维任务"])
app.include_router(ops.agent_router, prefix="/api", tags=["运维任务代理"])
app.include_router(oo_source.router, prefix="/api", tags=["OnlyOffice取件代理"])


@app.get("/api/health")
async def health():
    meili_status = "unknown"
    try:
        client = _get_search_client_sync()
        h = client.health()
        meili_status = h.get("status", "unknown")
    except Exception:
        meili_status = "unreachable"

    return {
        "status": "ok" if meili_status != "unreachable" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "meilisearch": meili_status,
    }


@app.get("/api/stats")
async def homepage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """首页统计：按当前用户可见分类过滤（部门管理员只看本部门+公共分类）。"""
    from sqlalchemy import false as sa_false

    perm = PermissionService(db, current_user)
    visible_ids = await perm.get_visible_category_ids()

    conditions = [Document.is_deleted == False]
    if current_user and current_user.role == "super_admin":
        pass  # 超管看全系统
    elif visible_ids:
        # 与文档列表接口一致：未分类文档（category_id IS NULL）不进入普通用户统计
        conditions.append(Document.category_id.in_(visible_ids))
    else:
        conditions.append(sa_false())

    total_docs = (await db.execute(
        select(func.count(Document.id)).where(*conditions)
    )).scalar() or 0

    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    week_updates = (await db.execute(
        select(func.count(Document.id)).where(*conditions, Document.updated_at >= week_ago)
    )).scalar() or 0

    if current_user and current_user.role == "super_admin":
        total_categories = (await db.execute(
            select(func.count(Category.id))
        )).scalar() or 0
    else:
        total_categories = (await db.execute(
            select(func.count(Category.id)).where(Category.id.in_(visible_ids))
        )).scalar() or 0 if visible_ids else 0

    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0

    return {
        "total_docs": total_docs,
        "week_updates": week_updates,
        "total_categories": total_categories,
        "active_users": active_users,
    }


# ── 一问一答助手（QA Assistant）反代 ─────────────────
QA_ASSISTANT_BACKEND = "http://127.0.0.1:7860"

@app.api_route("/qa/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def qa_assistant_proxy(path: str, request: Request):
    """把 /qa/* 转发给本地一问一答助手（Flask 7860），供前端悬浮球内嵌。"""
    url = f"{QA_ASSISTANT_BACKEND}/{path}" if path else f"{QA_ASSISTANT_BACKEND}/"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "connection")
    }
    body = await request.body()
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.request(
            request.method,
            url,
            headers=headers,
            content=body or None,
            params=request.query_params,
        )
    media_type = resp.headers.get("content-type", "text/html; charset=utf-8")
    return Response(content=resp.content, status_code=resp.status_code, media_type=media_type)


# ── 一问一答助手悬浮球片段（后端动态注入，前端重建不丢失）──
QA_FLOAT_FRAGMENT = (
    Path(__file__).resolve().parent.parent.parent
    / "qa_assistant" / "floatball_fragment.html"
)

# ── Serve the Vue SPA frontend ─────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: serve index.html for any non-API path.
        Vue Router handles client-side routing after index.html loads."""
        index_file = FRONTEND_DIST / "index.html"
        if not index_file.is_file():
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        html = index_file.read_text(encoding="utf-8", errors="replace")
        if QA_FLOAT_FRAGMENT.is_file() and "qa-float-root" not in html:
            fragment = QA_FLOAT_FRAGMENT.read_text(encoding="utf-8", errors="replace")
            html = html.replace("</body>", fragment + "\n</body>", 1)
        return Response(
            content=html,
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
