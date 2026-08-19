"""Markdown extraction pipeline for AI consumption.

Every knowledge-base document gets a machine-readable Markdown copy that is
stored both in PostgreSQL (markdown_content) and in MinIO (markdown_path).
Human-facing APIs deliberately do NOT expose these fields; AI systems use the
dedicated /api/ai endpoints with the AI_API_KEY.
"""
import asyncio
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.database import async_session_maker
from app.models.document import Document
from app.services.file_service import get_minio_client, _run_in_thread

logger = logging.getLogger(__name__)

MAX_MARKDOWN_LENGTH = 5_000_000  # ~5M chars, far beyond any reasonable doc

# Extensions markitdown can handle directly.
_MARKITDOWN_EXTS = {
    "pdf", "docx", "xlsx", "pptx", "txt", "md", "csv", "html", "htm", "xml", "json", "epub",
}

# Legacy / open-document formats: convert with LibreOffice first, then markitdown.
_LEGACY_EXTS = {
    "doc": ("docx",),
    "xls": ("xlsx",),
    "ppt": ("pptx",),
    "odt": ("docx",),
    "ods": ("xlsx",),
    "odp": ("pptx",),
}

_SUPPORTED_EXTS = _MARKITDOWN_EXTS | set(_LEGACY_EXTS)

# 图片：本地 PaddleOCR 服务做版面解析转 Markdown
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff"}
_SUPPORTED_EXTS = _SUPPORTED_EXTS | _IMAGE_EXTS

_IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
}

# Background tasks (strong refs avoid GC killing them, same pattern as previews).
_MD_TASKS: set[asyncio.Task] = set()
_MD_QUEUED: set[str] = set()

# Watermark fragments found on CMDE/NMPA cover pages. Removing them keeps the
# extracted Markdown readable without losing legitimate content.
_PDF_WATERMARKS = [
    re.compile(r"NMPA\s*ww"),
    re.compile(r"NMPA器审中心技术审评报告公开"),
    re.compile(r"NMPA器审中心技术审评报告"),
    re.compile(r"NMPA器审中心技术审评"),
    re.compile(r"NMPA器审中心技术"),
    re.compile(r"NMPA器审中"),
    re.compile(r"MPA器审中心技术审评报告公开"),
    re.compile(r"MPA器审中心技术审评报告"),
    re.compile(r"MPA器审中"),
    re.compile(r"器审中心技术审评报告公开"),
    re.compile(r"器审中心技术审评报告"),
    re.compile(r"器审中"),
    re.compile(r"心技术审评报告公开"),
    re.compile(r"心技术审评报告"),
    re.compile(r"技术审评报告公开"),
    re.compile(r"审评报告公开"),
    re.compile(r"告公开"),
    re.compile(r"www\.cmde\.org\.cng?\.cn"),
    re.compile(r"www\.cmde\.org\.cn"),
    re.compile(r"\bw\.cmde\.org\.cn"),
    re.compile(r"\b\.cmde\.org\.cn"),
    re.compile(r"\bg\.cn\b"),
    re.compile(r"\b心技\b"),
    re.compile(r"www\.cmd"),
    re.compile(r"\borg\.cng?\.cn"),
    re.compile(r"\be\.o\b"),
]
_PDF_WATERMARK_CHARS = set("开公告报审术评心技中")


def _clean_pdf_noise(text: str) -> str:
    """Strip CMDE/NMPA cover-page watermark noise from extracted text."""
    for pat in _PDF_WATERMARKS:
        text = pat.sub(" ", text)
    kept = []
    for line in text.splitlines():
        t = line.strip()
        if not t:
            kept.append("")
            continue
        if len(t) == 1 and t in _PDF_WATERMARK_CHARS:
            continue
        if re.fullmatch(r"[w\s]+", t):
            continue
        if t in (
            "NMPA", "MPA", "NMPA器", "NMPA器审", "NMPA器审中心", "www", "cmde",
            "org", "org.cn", "g.cn", "cn", "心技", "器审", "器审中", "公开", "告公开",
            "报告", "技术", "中心", "术审", "评报告", "技术审评", "审评", "技术审评报告",
        ):
            continue
        kept.append(t)
    out = "\n".join(kept)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _markitdown_text(content: bytes, filename: str) -> str:
    from markitdown import MarkItDown
    converter = MarkItDown(enable_plugins=False)
    result = converter.convert_stream(
        io.BytesIO(content), file_extension=f".{filename.rsplit('.', 1)[-1]}"
    )
    return (result.text_content or "").strip()


def _ocr_extract_markdown(content: bytes, filename: str) -> str:
    """扫描件/图片走本地 PaddleOCR（文档解析工作台）转 Markdown。

    失败或未配置时返回空串，由调用方走原有降级逻辑（fail-soft）。
    """
    base = (settings.OCR_API_URL or "").rstrip("/")
    key = settings.OCR_API_KEY or ""
    if not base or not key:
        return ""
    safe_name = os.path.basename(filename or "upload")
    # 响应头只接受 ASCII：中文文件名替换为下划线，保留扩展名
    ascii_name = re.sub(r"[^\x20-\x7e]", "_", safe_name) or "upload"
    mime = _IMAGE_MIME.get(ascii_name.rsplit(".", 1)[-1].lower(), "application/pdf")
    try:
        import httpx
        with httpx.Client(timeout=600) as client:
            resp = client.post(
                f"{base}/api/analyze",
                params={"mode": "document"},
                content=content,
                headers={
                    "x-api-key": key,
                    "x-filename": ascii_name,
                    "content-type": mime,
                },
            )
            resp.raise_for_status()
            md = (resp.json() or {}).get("markdown") or ""
            md = _sanitize_markdown(md).strip()
            if len(md) >= 50:
                return md
            return ""
    except Exception:
        logger.warning("OCR extraction failed for %s", filename, exc_info=True)
        return ""


def _extract_pdf_pymupdf(content: bytes) -> str:
    """Extract PDF text with PyMuPDF, dropping watermark layers.

    CMDE/NMPA cover pages overlay a gray (0x404040) watermark
    ("NMPA器审中心技术审评报告公开 www.cmde.org.cn") on top of black body
    text. Filtering spans by color + watermark keywords removes the overlay
    without touching legitimate content.
    """
    import pymupdf
    doc = pymupdf.open(stream=content, filetype="pdf")
    parts = []
    for page in doc:
        table_rects = []
        tables = []
        try:
            tables = page.find_tables().tables
            table_rects = [pymupdf.Rect(t.bbox) for t in tables]
        except Exception:
            table_rects = []
            tables = []

        items = []  # (y, kind, payload) kind: text | table
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) < 7 or block[6] != 0:
                continue
            x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
            center = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
            if any(rect.contains(center) for rect in table_rects):
                continue
            text = text.strip()
            if text:
                items.append((y0, "text", text))

        for table in tables:
            md_table = _table_to_markdown(table.extract())
            if md_table:
                items.append((table.bbox[1], "table", md_table))

        items.sort(key=lambda item: (item[0], item[1]))
        page_parts = [payload for _, _, payload in items]
        parts.append("\n".join(page_parts))
    return "\n".join(parts).strip()


def _table_to_markdown(rows: list[list]) -> str:
    """Convert PyMuPDF table rows into a clean Markdown table."""
    if not rows or not rows[0]:
        return ""
    num_cols = max(len(row) for row in rows)

    def norm(cell):
        if cell is None:
            return ""
        text = str(cell).replace("\n", " ").replace("|", "\\|").strip()
        # Drop a stray watermark char ("开"/"公"/"告"...) glued to cell start.
        text = re.sub(r"^[开公告报审术评心技中]\s+(?=[A-Z0-9０-９])", "", text)
        # ... or glued to the end ("16 开").
        text = re.sub(r"\s[开公告报审术评心技中]$", "", text)
        return text

    normalized = [[norm(row[i] if i < len(row) else None) for i in range(num_cols)] for row in rows]
    header = "| " + " | ".join(normalized[0]) + " |"
    sep = "|" + "|".join([" --- "] * num_cols) + "|"
    body = "\n".join("| " + " | ".join(row) + " |" for row in normalized[1:])
    return f"{header}\n{sep}\n{body}"


def _is_pdf_watermark_span(text: str, color: int) -> bool:
    """True when a span looks like the CMDE/NMPA watermark overlay."""
    if color == 0x404040 or color == 0x808080:
        markers = (
            "www.cmde.org.cn",
            "cmde.org",
            "器审中心技术审评报告公开",
            "NMPA器审中心",
            "MPA器审中心",
            "审评报告公开",
            "心技术审评报告公开",
        )
        return any(m in text for m in markers)
    return False


def _extract_pdf_pypdf(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def _md_cell(value) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _rows_to_markdown_table(
    title: str,
    rows: list[list[str]],
    extra_title: str = "",
) -> str:
    if not rows:
        return ""
    num_cols = max(len(r) for r in rows)
    while num_cols > 1 and all(
        (r[num_cols - 1] if num_cols - 1 < len(r) else "") == "" for r in rows
    ):
        num_cols -= 1
    lines = [f"## {title}", ""]
    if extra_title:
        lines.append(f"**{_md_cell(extra_title)}**")
        lines.append("")
    lines.append("| " + " | ".join(_md_cell(c) for c in rows[0][:num_cols]) + " |")
    lines.append("|" + "|".join([" --- "] * num_cols) + "|")
    for row in rows[1:]:
        cells = [_md_cell(row[i] if i < len(row) else "") for i in range(num_cols)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _extract_xlsx_markdown(content: bytes) -> str:
    """Clean xlsx -> Markdown tables (real header row, no Unnamed/NaN noise)."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        rows: list[list[str]] = []
        for row in wb[sheet_name].iter_rows(values_only=True):
            values = ["" if v is None else str(v).strip() for v in row]
            if any(values):
                rows.append(values)
        extra_title = ""
        header_rows = rows
        if (
            len(rows) > 1
            and sum(1 for v in rows[0] if v) <= 1
            and sum(1 for v in rows[1] if v) >= 2
        ):
            extra_title = rows[0][0]
            header_rows = [rows[1]] + rows[2:]
        table = _rows_to_markdown_table(sheet_name, header_rows, extra_title)
        if table:
            parts.append(table)
    wb.close()
    return "\n\n".join(parts)


def _extract_xls_markdown(content: bytes) -> str:
    """Clean legacy .xls -> Markdown tables."""
    import xlrd
    wb = xlrd.open_workbook(file_contents=content)
    parts = []
    for sheet in wb.sheets():
        rows: list[list[str]] = []
        for r in range(sheet.nrows):
            values = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
            if any(values):
                rows.append(values)
        extra_title = ""
        header_rows = rows
        if (
            len(rows) > 1
            and sum(1 for v in rows[0] if v) <= 1
            and sum(1 for v in rows[1] if v) >= 2
        ):
            extra_title = rows[0][0]
            header_rows = [rows[1]] + rows[2:]
        table = _rows_to_markdown_table(sheet.name, header_rows, extra_title)
        if table:
            parts.append(table)
    return "\n\n".join(parts)


def _sanitize_markdown(text: str) -> str:
    """Keep PostgreSQL-friendly UTF-8 text."""
    text = "".join(ch for ch in text if not (0xD800 <= ord(ch) <= 0xDFFF))
    text = text.replace("\x00", "").replace("�", "")
    return text[:MAX_MARKDOWN_LENGTH]


def _soffice_convert(content: bytes, src_ext: str, target_ext: str) -> bytes | None:
    """Convert legacy/ODF files to modern Office formats with LibreOffice.

    Prefers a host installation of LibreOffice; falls back to the soffice
    binary inside the gotenberg container (docker exec + docker cp).
    """
    with tempfile.TemporaryDirectory(prefix="mdconv_") as td:
        src_path = os.path.join(td, f"input.{src_ext}")
        out_dir = os.path.join(td, "out")
        os.makedirs(out_dir, exist_ok=True)
        with open(src_path, "wb") as fh:
            fh.write(content)

        # Isolated LibreOffice profile per invocation: concurrent headless
        # conversions otherwise fight over ~/.config/libreoffice and fail.
        lo_profile = f"file:///tmp/lo_profile_{uuid.uuid4().hex}"
        if shutil.which("soffice") or shutil.which("libreoffice"):
            binary = shutil.which("soffice") or shutil.which("libreoffice")
            cmd = [
                "ionice", "-c3", binary, f"-env:UserInstallation={lo_profile}",
                "--headless", "--norestore",
                "--convert-to", target_ext,
                "--outdir", out_dir, src_path,
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=180)
                if proc.returncode != 0:
                    logger.warning("soffice convert %s->%s failed: %s", src_ext, target_ext, proc.stderr[-300:])
                    return None
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return None
        else:
            # Fallback: use LibreOffice inside the gotenberg container.
            try:
                container_src = f"/tmp/mdconv/{uuid.uuid4().hex}/input.{src_ext}"
                container_dir = os.path.dirname(container_src)
                subprocess.run(
                    ["docker", "exec", "kb-gotenberg", "mkdir", "-p", container_dir],
                    capture_output=True, timeout=30, check=True,
                )
                subprocess.run(
                    ["docker", "cp", src_path, f"kb-gotenberg:{container_src}"],
                    capture_output=True, timeout=60, check=True,
                )
                subprocess.run(
                    [
                        "docker", "exec", "kb-gotenberg", "soffice",
                        f"-env:UserInstallation=/tmp/lo_{uuid.uuid4().hex}",
                        "--headless", "--norestore",
                        "--convert-to", target_ext,
                        "--outdir", container_dir, container_src,
                    ],
                    capture_output=True, timeout=180, check=True,
                )
                out_name = f"input.{target_ext}"
                subprocess.run(
                    [
                        "docker", "cp",
                        f"kb-gotenberg:{container_dir}/{out_name}",
                        os.path.join(out_dir, out_name),
                    ],
                    capture_output=True, timeout=60, check=True,
                )
            except subprocess.CalledProcessError:
                logger.warning("docker soffice fallback failed for %s", src_ext)
                return None

        out_files = [f for f in os.listdir(out_dir) if f.lower().endswith(f".{target_ext}")]
        if not out_files:
            return None
        with open(os.path.join(out_dir, out_files[0]), "rb") as fh:
            return fh.read()


def extract_markdown(content: bytes, filename: str) -> tuple[str, str]:
    """Return (markdown, status). status: done | unsupported."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _SUPPORTED_EXTS:
        return "", "unsupported"

    try:
        if ext == "pdf":
            candidates = []
            # Primary: PyMuPDF with real table detection (clean markdown tables,
            # body text in reading order). Fallbacks only when it yields too little.
            try:
                pymupdf_md = _clean_pdf_noise(_extract_pdf_pymupdf(content))
                if len(pymupdf_md) >= 100:
                    candidates.append(pymupdf_md)
            except Exception:
                pass
            if not candidates:
                for extractor in (_markitdown_text, _extract_pdf_pypdf):
                    try:
                        text = extractor(content, filename) if extractor is _markitdown_text else extractor(content)
                        cleaned = _clean_pdf_noise(text)
                        if cleaned:
                            candidates.append(cleaned)
                    except Exception:
                        continue
            if not candidates:
                # 扫描型 PDF（无文本层）→ 本地 PaddleOCR 版面解析
                ocr_md = _ocr_extract_markdown(content, filename)
                if ocr_md:
                    return _sanitize_markdown(ocr_md), "done"
                return "", "unsupported"
            best = max(candidates, key=_pdf_quality_score)
            if len(best) < 50:
                ocr_md = _ocr_extract_markdown(content, filename)
                if ocr_md:
                    return _sanitize_markdown(ocr_md), "done"
                return "", "unsupported"
            return _sanitize_markdown(best), "done"

        # 图片：本地 PaddleOCR 版面解析转 Markdown
        if ext in _IMAGE_EXTS:
            ocr_md = _ocr_extract_markdown(content, filename)
            if ocr_md:
                return _sanitize_markdown(ocr_md), "done"
            return "", "unsupported"

        # Excel: build clean markdown tables directly (markitdown leaves
        # "Unnamed: N" headers and NaN noise).
        if ext == "xlsx":
            try:
                md = _extract_xlsx_markdown(content)
                if md.strip():
                    return _sanitize_markdown(md), "done"
            except Exception:
                pass
            # Fallback: file may actually be legacy .xls or a broken xlsx.
            try:
                md = _extract_xls_markdown(content)
                if md.strip():
                    return _sanitize_markdown(md), "done"
            except Exception:
                pass
            converted = _soffice_convert(content, "xlsx", "xlsx")
            if converted:
                try:
                    md = _extract_xlsx_markdown(converted)
                    if md.strip():
                        return _sanitize_markdown(md), "done"
                except Exception:
                    pass
            return "", "failed"
        elif ext == "xls":
            try:
                md = _extract_xls_markdown(content)
                if md.strip():
                    return _sanitize_markdown(md), "done"
            except Exception:
                pass
            converted = _soffice_convert(content, "xls", "xlsx")
            if converted:
                try:
                    md = _extract_xlsx_markdown(converted)
                    if md.strip():
                        return _sanitize_markdown(md), "done"
                except Exception:
                    pass
            return "", "failed"

        if ext == "docx":
            try:
                md_text = _markitdown_text(content, filename)
                if md_text.strip():
                    return _sanitize_markdown(md_text), "done"
            except Exception:
                pass
            # Fallback: mislabeled .doc or a broken docx — rebuild via LibreOffice.
            for src_ext in ("docx", "doc"):
                converted = _soffice_convert(content, src_ext, "docx")
                if not converted:
                    continue
                try:
                    md_text = _markitdown_text(converted, "input.docx")
                    if md_text.strip():
                        return _sanitize_markdown(md_text), "done"
                except Exception:
                    continue
            return "", "failed"

        if ext in _LEGACY_EXTS:
            target_ext = _LEGACY_EXTS[ext][0]
            converted = _soffice_convert(content, ext, target_ext)
            if converted is None:
                return "", "failed"
            content, filename = converted, f"input.{target_ext}"

        md_text = _markitdown_text(content, filename)
        if not md_text:
            return "", "unsupported"
        return _sanitize_markdown(md_text), "done"
    except Exception:
        logger.warning("markitdown extraction failed for %s", filename, exc_info=True)
        return "", "failed"


def _pdf_quality_score(text: str) -> int:
    """Prefer complete text that stays readable: penalize watermark leftovers."""
    lines = [ln.strip() for ln in text.splitlines()]
    nonempty = [ln for ln in lines if ln]
    wm_hits = sum(text.count(p.pattern) for p in _PDF_WATERMARKS)
    junk = sum(
        1
        for ln in nonempty
        if len(ln) <= 3 and re.fullmatch(r"[开公告报审术评心技中wWcCoOrRgGnN\./|—\-]+", ln)
    )
    single = sum(1 for ln in nonempty if len(ln) == 1)
    return len(text) - 120 * wm_hits - 30 * junk - 15 * single


async def _read_from_minio(s3_path: str) -> bytes | None:
    try:
        s3 = get_minio_client()
        bucket_key = s3_path[5:]
        bucket, key = bucket_key.split("/", 1)
        resp = await _run_in_thread(s3.get_object, Bucket=bucket, Key=key)
        return await _run_in_thread(lambda: resp["Body"].read())
    except Exception:
        logger.warning("Failed to read from MinIO: %s", s3_path, exc_info=True)
        return None


async def _upload_markdown(md_text: str, original_filename: str) -> str | None:
    try:
        s3 = get_minio_client()
        stem = os.path.splitext(original_filename or "document")[0]
        key = f"markdowns/{uuid.uuid4().hex}/{stem}.md"
        await _run_in_thread(
            s3.upload_fileobj,
            io.BytesIO(md_text.encode("utf-8")),
            settings.MINIO_BUCKET,
            key,
            ExtraArgs={"ContentType": "text/markdown; charset=utf-8"},
        )
        return f"s3://{settings.MINIO_BUCKET}/{key}"
    except Exception:
        logger.warning("Failed to upload markdown for %s", original_filename, exc_info=True)
        return None


async def generate_markdown_for_doc(doc_id: str) -> None:
    """Generate and persist Markdown for one document. Safe to call repeatedly."""
    try:
        async with async_session_maker() as db:
            import uuid as _uuid
            doc = await db.get(Document, _uuid.UUID(doc_id))
            if not doc or doc.is_deleted:
                return
            if doc.markdown_status == "done":
                return

            # Link articles: markdown is the article text itself.
            if doc.file_type == "link":
                if doc.content_text and doc.content_text.strip():
                    doc.markdown_content = _sanitize_markdown(doc.content_text)
                    doc.markdown_status = "done"
                    doc.markdown_updated_at = datetime.now(timezone.utc)
                    await db.commit()
                else:
                    doc.markdown_status = "pending"
                    await db.commit()
                return

            content = await _read_from_minio(doc.original_path)
            if content is None:
                doc.markdown_status = "failed"
                doc.markdown_updated_at = datetime.now(timezone.utc)
                await db.commit()
                return

            md_text, status = await asyncio.to_thread(
                extract_markdown, content, doc.original_filename
            )
            if status == "done":
                md_path = await _upload_markdown(md_text, doc.original_filename)
                doc.markdown_content = md_text
                doc.markdown_path = md_path
                doc.markdown_status = "done"
                doc.markdown_updated_at = datetime.now(timezone.utc)
            else:
                doc.markdown_status = status
                doc.markdown_updated_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        logger.warning("Markdown generation failed for %s", doc_id, exc_info=True)
        async with async_session_maker() as db:
            try:
                import uuid as _uuid
                doc = await db.get(Document, _uuid.UUID(doc_id))
                if doc and doc.markdown_status != "done":
                    doc.markdown_status = "failed"
                    doc.markdown_updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


def queue_markdown_generation(doc_id: str) -> None:
    """Fire-and-forget background markdown generation (keeps strong refs)."""
    if doc_id in _MD_QUEUED:
        return
    _MD_QUEUED.add(doc_id)

    async def _runner():
        try:
            await generate_markdown_for_doc(doc_id)
        finally:
            _MD_QUEUED.discard(doc_id)

    task = asyncio.create_task(_runner())
    _MD_TASKS.add(task)
    task.add_done_callback(_MD_TASKS.discard)
