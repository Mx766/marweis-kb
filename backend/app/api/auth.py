from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import create_token, verify_password, get_current_user
from app.config import settings
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, UserProfile

router = APIRouter()

# Simple in-memory rate limiter for login
_login_attempts: dict[str, tuple[int, float]] = {}  # client_ip -> (count, window_start)
_LOGIN_RATE_LIMIT = 10      # max attempts
_LOGIN_RATE_WINDOW = 300    # seconds (5 minutes)


def _check_login_rate_limit(client_ip: str) -> None:
    """Raise 429 if the client has exceeded the login rate limit."""
    import time
    now = time.time()
    count, window_start = _login_attempts.get(client_ip, (0, now))
    if now - window_start > _LOGIN_RATE_WINDOW:
        count, window_start = 0, now
    if count >= _LOGIN_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    _login_attempts[client_ip] = (count + 1, window_start)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    import time
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已停用")

    token = create_token(str(user.id))
    # Calculate actual token expiration timestamp
    actual_expire_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    return LoginResponse(
        token=token,
        user=UserProfile.from_orm(user),
        expires_at=str(int(actual_expire_at.timestamp())),
    )


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)):
    return UserProfile.from_orm(current_user)
