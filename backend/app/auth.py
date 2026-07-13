import re
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Password strength ──────────────────────────────────────
_MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password is too weak, or None if valid."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"密码长度不能少于 {_MIN_PASSWORD_LENGTH} 位"
    if not re.search(r"[A-Za-z]", password):
        return "密码必须包含至少一个字母"
    if not re.search(r"\d", password):
        return "密码必须包含至少一个数字"
    return None


# ── Token ───────────────────────────────────────────────────

def create_token(user_id: str, expire_hours: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=expire_hours or settings.JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="无效或过期的认证令牌")


# ── Dependencies ────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="用户不存在或已停用")
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user = await db.get(User, payload["sub"])
        if user and user.is_active:
            return user
        return None
    except HTTPException:
        return None


def require_role(*roles: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user
    return checker


def require_department(*departments: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == "super_admin":
            return current_user
        if current_user.department not in departments:
            raise HTTPException(status_code=403, detail="无权访问该部门资源")
        return current_user
    return checker
