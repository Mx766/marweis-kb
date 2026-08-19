# -*- coding: utf-8 -*-
"""OnlyOffice 服务器端取件代理。

OnlyOffice 拉取文档时如果直接请求 MinIO 预签名 URL，偶发 400（其 HTTP 客户端与
MinIO 的 keep-alive/请求解析存在兼容问题）。这里提供一条干净路径：
OnlyOffice -> 后端 -> boto3 从 MinIO 取流，无预签名查询串，稳定返回文件内容。
"""
import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import time
import uuid as _uuid
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.document import Document
from app.models.user_file import UserFile
from app.services.file_service import get_minio_client

router = APIRouter(prefix="/onlyoffice/source", tags=["OnlyOffice取件代理"])

TOKEN_TTL = 600  # 10 分钟，OnlyOffice 打开时即时拉取足够


def _sign(payload: str) -> str:
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def make_source_token(kind: str, obj_id: str) -> str:
    """生成取件 token（HMAC 签名 + 过期时间）。kind: file=公盘, doc=知识库。"""
    raw = base64.urlsafe_b64encode(
        json.dumps(
            {"k": kind, "i": obj_id, "e": int(time.time()) + TOKEN_TTL},
            separators=(",", ":"),
        ).encode("utf-8")
    ).decode("ascii")
    payload = raw.rstrip("=")
    return payload + "." + _sign(payload)


def _parse_token(token: str) -> dict:
    try:
        payload, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            raise ValueError("bad signature")
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))
        if int(data.get("e", 0)) < time.time():
            raise ValueError("expired")
        return data
    except Exception:
        raise HTTPException(401, "取件链接无效或已过期")


async def _resolve_object(data: dict) -> tuple[str, str, str]:
    kind = data.get("k")
    obj_id = data.get("i")
    async with async_session_maker() as db:
        if kind == "file":
            row = (
                await db.execute(
                    select(UserFile).where(
                        UserFile.id == _uuid.UUID(str(obj_id)),
                        UserFile.is_deleted.is_(False),
                        UserFile.is_folder.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not row:
                raise HTTPException(404, "文件不存在")
            return row.file_path, row.filename or "file", row.file_ext or ""
        if kind == "doc":
            row = await db.get(Document, _uuid.UUID(str(obj_id)))
            if not row or row.is_deleted:
                raise HTTPException(404, "文档不存在")
            op = row.original_path or ""
            if not op.startswith("s3://"):
                raise HTTPException(400, "非文件型文档")
            key = op.split("/", 3)[-1]
            return key, row.original_filename or row.title or "file", row.file_ext or ""
    raise HTTPException(400, "未知取件类型")


@router.get("/{token}")
async def source(token: str):
    data = _parse_token(token)
    key, filename, ext = await _resolve_object(data)
    if not key or key.startswith(("http://", "https://")):
        raise HTTPException(400, "文件无存储对象")

    s3 = get_minio_client()
    bucket = settings.MINIO_BUCKET
    try:
        obj = await asyncio.to_thread(
            s3.get_object,
            Bucket=bucket,
            Key=key,
        )
    except Exception:
        raise HTTPException(404, "文件不存在")

    body = obj["Body"]
    media = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    def gen():
        try:
            while True:
                chunk = body.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            body.close()

    safe_name = quote(filename, safe="")
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{safe_name}",
        "Cache-Control": "private, max-age=60",
    }
    length = obj.get("ContentLength")
    if length:
        headers["Content-Length"] = str(length)
    return StreamingResponse(gen(), media_type=media, headers=headers)
