from fastapi import Request
from fastapi.responses import JSONResponse


async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for the entire application."""
    import traceback
    from app.config import settings
    traceback.print_exc()
    response_content: dict = {"detail": "服务器内部错误，请稍后重试"}
    # Only expose error type in development
    if settings.ENVIRONMENT == "development":
        response_content["error_type"] = type(exc).__name__
    return JSONResponse(status_code=500, content=response_content)
