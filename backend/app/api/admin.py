from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, require_role, hash_password, validate_password_strength
from app.config import DEPARTMENTS, ROLES
from app.models.user import User
from app.schemas import UserCreate, UserUpdate, UserItem, UserListResponse
import uuid as _uuid
import datetime as _datetime

router = APIRouter()


def _user_to_item(user: User) -> UserItem:
    return UserItem(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        employee_id=user.employee_id,
        department=user.department,
        role=user.role,
        email=user.email,
        is_active=user.is_active,
        created_at=str(user.created_at),
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    department: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    conditions = []
    if department:
        conditions.append(User.department == department)
    if current_user.role == "dept_admin":
        conditions.append(User.department == current_user.department)

    query = select(User).where(*conditions).order_by(User.created_at.desc())
    count_query = select(func.count(User.id)).where(*conditions)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    users = result.scalars().all()

    items = [_user_to_item(u) for u in users]
    return UserListResponse(items=items, total=total, page=page, size=size)


@router.post("/users")
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    existing = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Validate password strength
    pw_error = validate_password_strength(body.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    # Validate department and role
    if body.department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"无效的部门: {body.department}")
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {body.role}")

    # dept_admin can only create users in their own department with limited roles
    if current_user.role == "dept_admin":
        if body.department != current_user.department:
            raise HTTPException(status_code=403, detail="部门管理员只能在本部门创建用户")
        if body.role not in ("editor", "employee", "guest"):
            raise HTTPException(status_code=403, detail="部门管理员只能创建编辑者/员工/访客角色")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        employee_id=body.employee_id,
        department=body.department,
        role=body.role,
        email=body.email,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return _user_to_item(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin")),
):
    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "dept_admin":
        if user.department != current_user.department:
            raise HTTPException(status_code=403, detail="无权操作其他部门用户")
        # dept_admin cannot change a user's department to a different one
        if "department" in body.model_dump(exclude_unset=True):
            if body.department != current_user.department:
                raise HTTPException(status_code=403, detail="部门管理员不能将用户转移到其他部门")

    update_data = body.model_dump(exclude_unset=True)

    # Validate department and role if they are being updated
    if "department" in update_data and update_data["department"] not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"无效的部门: {update_data['department']}")
    if "role" in update_data and update_data["role"] not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {update_data['role']}")

    # dept_admin cannot escalate user to super_admin or dept_admin
    if current_user.role == "dept_admin" and "role" in update_data:
        if update_data["role"] not in ("editor", "employee", "guest"):
            raise HTTPException(status_code=403, detail="部门管理员不能授予此角色")
        # dept_admin cannot change role of super_admin or other dept_admins
        if user.role in ("super_admin", "dept_admin"):
            raise HTTPException(status_code=403, detail="无权修改管理员角色的用户")

    for key, val in update_data.items():
        setattr(user, key, val)
    await db.flush()
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    await db.delete(user)
    await db.flush()
    await db.commit()
    return {"message": "用户已删除"}
