import time
import threading
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import create_token, verify_password, hash_password, validate_password_strength, get_current_user, require_role
from app.config import settings, DEPARTMENTS
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, ChangePasswordRequest, UserProfile

router = APIRouter()

# ── Login rate limiter with automatic TTL-based expiry ─────
_LOGIN_RATE_LIMIT = 10      # max attempts per window
_LOGIN_RATE_WINDOW = 300    # seconds (5 minutes)
_CLEANUP_INTERVAL = 600     # background cleanup every 10 minutes

_login_attempts: dict[str, tuple[int, float]] = {}  # client_ip -> (count, window_start)
_lock = threading.Lock()
_last_cleanup = time.time()

# 账号锁定：同 IP+账号 5 次失败锁 15 分钟
_LOGIN_FAIL_WINDOW = 15 * 60
_LOGIN_FAIL_MAX = 5
_login_fails: dict[str, list[float]] = {}


def _check_login_rate_limit(client_ip: str, username: str) -> None:
    """Raise 429 if the client has exceeded the login rate limit.

    Keyed by IP + username so users behind the same public IP (office NAT)
    do not block each other. Uses a simple dict with periodic background
    cleanup to prevent unbounded memory growth.
    """
    global _last_cleanup
    now = time.time()
    key = f"{client_ip}|{username}"

    with _lock:
        # Periodic cleanup of all expired entries (not just on new requests)
        if now - _last_cleanup > _CLEANUP_INTERVAL:
            expired = [k for k, (_, ws) in _login_attempts.items() if now - ws > _LOGIN_RATE_WINDOW]
            for ip in expired:
                del _login_attempts[ip]
            _last_cleanup = now

        count, window_start = _login_attempts.get(key, (0, now))
        if now - window_start > _LOGIN_RATE_WINDOW:
            count, window_start = 0, now
        if count >= _LOGIN_RATE_LIMIT:
            raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
        _login_attempts[key] = (count + 1, window_start)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip, body.username)
    fail_key = f"{client_ip}|{body.username}"
    now = time.time()
    fails = [t for t in _login_fails.get(fail_key, []) if now - t < _LOGIN_FAIL_WINDOW]
    _login_fails[fail_key] = fails
    if len(fails) >= _LOGIN_FAIL_MAX:
        raise HTTPException(status_code=423, detail="登录失败次数过多，请15分钟后再试")
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        _login_fails.setdefault(fail_key, []).append(now)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已停用")
    _login_fails.pop(fail_key, None)

    token = create_token(str(user.id))
    # Calculate actual token expiration timestamp
    actual_expire_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    return LoginResponse(
        token=token,
        user=UserProfile.from_orm(user),
        expires_at=str(int(actual_expire_at.timestamp())),
    )


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Admin-only: create a new user account. Employees cannot self-register."""
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


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码（需验证原密码）"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    pw_error = validate_password_strength(body.new_password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True, "message": "密码已修改"}
