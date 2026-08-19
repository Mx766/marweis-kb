import asyncio
import logging
import httpx
import os
import boto3
import uuid
from io import BytesIO
from botocore.config import Config as BotoConfig
from app.config import settings

logger = logging.getLogger(__name__)


def _build_minio_client(endpoint: str, *, secure: bool | None = None) -> object:
    """Create a boto3 S3 client for the given MinIO endpoint."""
    use_https = settings.MINIO_SECURE if secure is None else secure
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if use_https else 'http'}://{endpoint}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
    )


def get_minio_client():
    """Return a boto3 S3 client for internal MinIO operations."""
    return _build_minio_client(settings.MINIO_ENDPOINT)


def _get_presigned_client():
    """Return a boto3 S3 client configured with the PUBLIC endpoint.
    Presigned URLs must be signed with the endpoint that external clients use.
    """
    endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
    return _build_minio_client(endpoint, secure=settings.MINIO_PUBLIC_SECURE)


def _get_onlyoffice_client():
    """Return a boto3 S3 client for OnlyOffice server-side document fetching.

    OnlyOffice 容器与 MinIO 同在内网时优先走内网直连，避免公网 frp 链路抖动导致
    间歇性 400；未配置 MINIO_ONLYOFFICE_ENDPOINT 时回退到公网 endpoint。
    """
    if not settings.MINIO_ONLYOFFICE_ENDPOINT:
        return _get_presigned_client()
    return _build_minio_client(
        settings.MINIO_ONLYOFFICE_ENDPOINT,
        secure=settings.MINIO_ONLYOFFICE_SECURE,
    )


def _ensure_bucket_exists(s3):
    """Create the MinIO bucket if it doesn't already exist."""
    try:
        s3.head_bucket(Bucket=settings.MINIO_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=settings.MINIO_BUCKET)
        logger.info("Created MinIO bucket: %s", settings.MINIO_BUCKET)


async def _run_in_thread(func, *args, **kwargs):
    """Run a synchronous I/O call in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(lambda: func(*args, **kwargs))


class FileService:
    """Handles file upload, MinIO storage, and Gotenberg-based document conversion."""

    @staticmethod
    async def upload_and_convert(
        file_content: bytes,
        original_filename: str,
        content_type: str,
    ) -> dict:
        """Upload file to MinIO, trigger Gotenberg conversion, return metadata."""
        file_ext = os.path.splitext(original_filename)[1].lower().lstrip(".")
        file_size = len(file_content)

        # 1. Store original in MinIO (offloaded to thread to avoid blocking)
        s3 = get_minio_client()
        await _run_in_thread(_ensure_bucket_exists, s3)

        object_key = f"originals/{uuid.uuid4()}/{original_filename}"
        await _run_in_thread(s3.upload_fileobj, BytesIO(file_content), settings.MINIO_BUCKET, object_key)

        original_path = f"s3://{settings.MINIO_BUCKET}/{object_key}"

        # 2. Convert to preview format via Gotenberg
        preview_path = await FileService._convert_preview(file_content, original_filename, file_ext)

        return {
            "original_path": original_path,
            "preview_path": preview_path,
            "file_size": file_size,
            "file_ext": file_ext,
            "mime_type": content_type,
        }

    @staticmethod
    async def _convert_preview(file_content: bytes, filename: str, ext: str) -> str | None:
        """Convert document to preview PDF via Gotenberg. Returns preview S3 path or None."""
        CONVERTIBLE = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "odp", "ods"}

        if ext.lower() not in CONVERTIBLE:
            return None

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                files = {"files": (filename, file_content)}
                response = await client.post(
                    f"{settings.GOTENBERG_URL}/forms/libreoffice/convert",
                    files=files,
                )
                if response.status_code != 200:
                    logger.warning(
                        "Gotenberg conversion returned %d for %s",
                        response.status_code, filename,
                    )
                    return None

                s3 = get_minio_client()
                await _run_in_thread(_ensure_bucket_exists, s3)

                preview_key = f"previews/{uuid.uuid4()}/{os.path.splitext(filename)[0]}.pdf"
                await _run_in_thread(s3.upload_fileobj, BytesIO(response.content), settings.MINIO_BUCKET, preview_key)

                return f"s3://{settings.MINIO_BUCKET}/{preview_key}"
        except Exception:
            logger.warning("Gotenberg conversion failed for %s", filename, exc_info=True)
            return None

    @staticmethod
    async def get_download_url(object_path: str, filename: str) -> str:
        """Generate a pre-signed URL for download (forces browser download dialog)."""
        return await FileService._presigned_url(object_path, filename, inline=False)

    @staticmethod
    async def get_preview_url(object_path: str, filename: str) -> str:
        """Generate a pre-signed URL for inline preview (browser displays, not downloads)."""
        return await FileService._presigned_url(object_path, filename, inline=True)

    @staticmethod
    async def get_onlyoffice_url(object_path: str, filename: str) -> str:
        """OnlyOffice 服务器端拉取文件用的预签名 URL（优先内网直连 MinIO）。"""
        return await FileService._presigned_url(
            object_path,
            filename,
            inline=True,
            client=_get_onlyoffice_client(),
        )

    @staticmethod
    async def _presigned_url(
        object_path: str,
        filename: str,
        *,
        inline: bool,
        client: object | None = None,
    ) -> str:
        """Generate a pre-signed URL for direct access from MinIO."""
        if not object_path.startswith("s3://"):
            return object_path  # External link, return as-is

        bucket_key = object_path[5:]  # strip "s3://"
        bucket, key = bucket_key.split("/", 1)

        # Use the PUBLIC endpoint client so the signature matches the URL clients see
        s3 = client or _get_presigned_client()

        try:
            params: dict = {"Bucket": bucket, "Key": key}
            # For download: force browser's save-as dialog.
            # For preview: omit ContentDisposition so the browser renders inline.
            if not inline:
                params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

            url = await _run_in_thread(
                s3.generate_presigned_url,
                "get_object",
                Params=params,
                ExpiresIn=settings.MINIO_PRESIGNED_EXPIRES,
            )
            return url
        except Exception:
            logger.warning("Failed to generate presigned URL for %s", object_path, exc_info=True)
            return object_path
