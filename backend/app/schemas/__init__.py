import uuid
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional, Any


# ─── Auth ────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: "UserProfile"
    expires_at: str


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str
    employee_id: str | None = None
    department: str
    role: str
    email: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: Any) -> "UserProfile":
        """Convert a User ORM instance to a UserProfile schema."""
        return cls(
            id=str(obj.id),
            username=obj.username,
            display_name=obj.display_name,
            employee_id=obj.employee_id,
            department=obj.department,
            role=obj.role,
            email=obj.email,
            avatar_url=obj.avatar_url,
        )


# ─── Category ────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None
    visible_departments: list[str] | None = None
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None
    icon: str | None = None
    visible_departments: list[str] | None = None
    description: str | None = None


class CategoryNode(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None
    visible_departments: list[str] | None = None
    description: str | None = None
    children: list["CategoryNode"] = []
    document_count: int = 0

    model_config = {"from_attributes": True}


class CategoryTree(BaseModel):
    categories: list[CategoryNode]


# ─── Document ────────────────────────────────────────
class DocumentCreate(BaseModel):
    title: str
    category_id: str | None = None
    tags: list[str] | None = None
    summary: str | None = None
    source: str | None = None
    source_url: str | None = None
    effective_date: date | None = None
    version: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None
    summary: str | None = None
    source: str | None = None
    source_url: str | None = None
    effective_date: date | None = None
    version: str | None = None


class DocumentItem(BaseModel):
    id: str
    title: str
    category_id: str | None = None
    file_type: str
    original_filename: str
    file_size: int = 0
    file_ext: str = ""
    mime_type: str = ""
    tags: list[str] | None = None
    summary: str | None = None
    source: str | None = None
    source_url: str | None = None
    effective_date: str | None = None
    version: str | None = None
    uploader_name: str = ""
    view_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentItem):
    preview_path: str | None = None
    original_path: str | None = None
    download_count: int = 0
    is_favorited: bool = False
    preview_url: str | None = None  # Presigned URL for inline browser preview


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]
    total: int
    page: int
    size: int
    pages: int


# ─── Search ──────────────────────────────────────────
class SearchResult(BaseModel):
    items: list[DocumentItem]
    total: int
    query: str
    page: int
    size: int


# ─── User Management ─────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    employee_id: str | None = None
    department: str
    role: str = "employee"
    email: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    employee_id: str | None = None
    department: str | None = None
    role: str | None = None
    email: str | None = None
    is_active: bool | None = None


class UserItem(BaseModel):
    id: str
    username: str
    display_name: str
    employee_id: str | None = None
    department: str
    role: str
    email: str | None = None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserItem]
    total: int
    page: int
    size: int


# ─── Personal ────────────────────────────────────────
class PersonalStats(BaseModel):
    total_uploads: int = 0
    total_favorites: int = 0
    total_history: int = 0
