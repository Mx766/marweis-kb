from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api import auth, categories, documents, search, personal, admin
from app.middleware.error_handler import global_exception_handler

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(categories.router, prefix="/api/categories", tags=["分类"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])
app.include_router(personal.router, prefix="/api/me", tags=["个人中心"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
