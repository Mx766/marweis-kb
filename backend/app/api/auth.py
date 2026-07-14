import time
import threading
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import create_token, verify_password, hash_password, validate_password_strength, get_current_user
from app.config import settings, DEPARTMENTS
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, UserProfile

router = APIRouter()

# ── Login rate limiter with automatic TTL-based expiry ─────
_LOGIN_RATE_LIMIT = 10      # max attempts per window
_LOGIN_RATE_WINDOW = 300    # seconds (5 minutes)
_CLEANUP_INTERVAL = 600     # background cleanup every 10 minutes

_login_attempts: dict[str, tuple[int, float]] = {}  # client_ip -> (count, window_start)
_lock = threading.Lock()
_last_cleanup = time.time()


def _check_login_rate_limit(client_ip: str) -> None:
    """Raise 429 if the client has exceeded the login rate limit.

    Uses a simple dict with periodic background cleanup to prevent
    unbounded memory growth from diverse client IPs.
    """
    global _last_cleanup
    now = time.time()

    with _lock:
        # Periodic cleanup of all expired entries (not just on new requests)
        if now - _last_cleanup > _CLEANUP_INTERVAL:
            expired = [ip for ip, (_, ws) in _login_attempts.items() if now - ws > _LOGIN_RATE_WINDOW]
            for ip in expired:
                del _login_attempts[ip]
            _last_cleanup = now

        count, window_start = _login_attempts.get(client_ip, (0, now))
        if now - window_start > _LOGIN_RATE_WINDOW:
            count, window_start = 0, now
        if count >= _LOGIN_RATE_LIMIT:
            raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
        _login_attempts[client_ip] = (count + 1, window_start)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)
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


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Self-registration — creates a new user with 'employee' role."""
    # Validate username uniqueness
    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Validate department
    if body.department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"无效的部门: {body.department}")

    # Validate password strength
    pw_error = validate_password_strength(body.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        department=body.department,
        role="employee",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    return {"message": "注册成功", "username": user.username}


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)):
    return UserProfile.from_orm(current_user)
