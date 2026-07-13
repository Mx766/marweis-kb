import logging
import time
from fastapi import Request

logger = logging.getLogger("marweis.request")


async def request_logging_middleware(request: Request, call_next):
    """Log incoming requests with method, path, status, and duration."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response
