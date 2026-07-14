import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api import auth, categories, documents, search, personal, admin, system
from app.middleware.error_handler import global_exception_handler
from app.middleware.logging import request_logging_middleware
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
app.include_router(system.router, prefix="/api/admin", tags=["系统设置"])


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


# ── Serve the Vue SPA frontend ─────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: serve index.html for any non-API path.
        Vue Router handles client-side routing after index.html loads."""
        index_file = FRONTEND_DIST / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
