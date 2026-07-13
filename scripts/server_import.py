#!/usr/bin/env python3
"""
Server-side high-speed import: MinIO + PostgreSQL, bypass API
Files already at /tmp/kb_import
"""
import os, sys, uuid, json
from datetime import datetime, timezone
from pathlib import Path
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import boto3
import requests

DATABASE_URL = "postgresql+asyncpg://marweis:marweis_dev@localhost:5432/marweis_kb"
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"
MINIO_BUCKET = "marweis-documents"
SOURCE_DIR = "/tmp/kb_import"
ADMIN_ID = "26a241f9-35d2-4ac1-bc6b-83cf86c37535"

CAT_MAP = {}

def load_cats():
    r = requests.get("http://localhost:8000/api/categories")
    def walk(nodes):
        for n in nodes:
            CAT_MAP[n["name"]] = n["id"]
            walk(n.get("children", []))
    walk(r.json())
    # Ensure subcategories from earlier import run
    for name, parent in [
        ("审评报告", "NMPA 法规库"),
        ("指导原则", "NMPA 法规库"),
        ("医疗器械审评报告", "审评报告"),
        ("体外诊断试剂审评报告", "审评报告"),
        ("医疗器械指导原则", "指导原则"),
        ("IVD指导原则", "指导原则"),
        ("分类目录", "NMPA 法规库"),
    ]:
        if name not in CAT_MAP:
            CAT_MAP[name] = CAT_MAP.get(parent)
    print(f"[OK] {len(CAT_MAP)} categories")

def get_s3():
    s3 = boto3.client("s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET)
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except:
        s3.create_bucket(Bucket=MINIO_BUCKET)
    return s3

async def batch_insert(batch):
    engine = create_async_engine(DATABASE_URL)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        for doc in batch:
            now = datetime.now(timezone.utc)
            await session.execute(text("""INSERT INTO documents (
                id, title, category_id, file_type, original_filename,
                original_path, preview_path, file_size, file_ext, mime_type,
                tags, summary, source, source_url,
                uploader_id, view_count, download_count, is_deleted, created_at, updated_at
            ) VALUES (
                :id, :title, :category_id, 'file', :original_filename,
                :original_path, NULL, :file_size, :file_ext, 'application/octet-stream',
                :tags, '', '', NULL,
                :uploader_id, 0, 0, false, :created_at, :updated_at
            ) ON CONFLICT DO NOTHING"""), {
                "id": doc["id"],
                "title": doc["title"],
                "category_id": doc["category_id"],
                "original_filename": doc["original_filename"],
                "original_path": doc["original_path"],
                "file_size": doc["file_size"],
                "file_ext": doc["file_ext"],
                "tags": json.dumps(doc.get("tags", [])),
                "uploader_id": doc["uploader_id"],
                "created_at": now,
                "updated_at": now,
            })
        await session.commit()
    await engine.dispose()

def determine_category(filepath, rel_path):
    parts = Path(rel_path).parts
    title = filepath.stem
    top = parts[0] if parts else ""

    if top.startswith("07"):
        if "FDA" in title or "21 CFR" in title:
            return CAT_MAP.get("FDA 法规库", list(CAT_MAP.values())[0]), ["法规", "FDA"]
        if "EU" in title or "MDR" in title or "IVDR" in title:
            return CAT_MAP.get("CE MDR 法规库", list(CAT_MAP.values())[0]), ["法规", "CE MDR"]
        return CAT_MAP.get("NMPA 法规库", list(CAT_MAP.values())[0]), ["法规", "NMPA"]

    if top.startswith("01"):
        return CAT_MAP.get("分类目录") or CAT_MAP.get("NMPA 法规库"), ["分类目录"]
    if top.startswith("02"):
        return CAT_MAP.get("NMPA 法规库"), ["豁免临床评价"]
    if top.startswith("03"):
        return CAT_MAP.get("NMPA 法规库"), ["临床路径"]
    if top.startswith("04"):
        return CAT_MAP.get("公共知识区") or CAT_MAP.get("NMPA 法规库"), ["产品库"]

    if top.startswith("05"):
        if len(parts) > 1:
            sub = parts[1]
            if "体外" in sub:
                return CAT_MAP.get("体外诊断试剂审评报告") or CAT_MAP.get("审评报告"), ["审评报告", "体外诊断试剂"]
            if "医疗" in sub and len(parts) > 2:
                return CAT_MAP.get(parts[2]) or CAT_MAP.get("医疗器械审评报告"), ["审评报告", "医疗器械"]
        return CAT_MAP.get("审评报告"), ["审评报告"]

    if top.startswith("06"):
        if len(parts) > 1:
            sub = parts[1]
            if "体外" in sub:
                return CAT_MAP.get("IVD指导原则") or CAT_MAP.get("指导原则"), ["指导原则", "体外诊断试剂"]
            if "医疗" in sub and len(parts) > 2:
                return CAT_MAP.get(parts[2]) or CAT_MAP.get("医疗器械指导原则"), ["指导原则", "医疗器械"]
        return CAT_MAP.get("指导原则"), ["指导原则"]

    fallback = list(CAT_MAP.values())[0] if CAT_MAP else None
    return fallback, []


async def main():
    load_cats()
    s3 = get_s3()

    all_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for fname in files:
            fpath = Path(root) / fname
            if fname.startswith("~$"):
                continue
            all_files.append((fpath, str(fpath.relative_to(SOURCE_DIR))))

    print(f"Files to import: {len(all_files)}")

    batch = []
    ok = fail = 0

    for i, (fpath, rel) in enumerate(all_files):
        try:
            obj_key = f"originals/{uuid.uuid4()}/{fpath.name}"
            with open(fpath, "rb") as f:
                s3.upload_fileobj(f, MINIO_BUCKET, obj_key)

            cat_id, tags = determine_category(fpath, rel)
            if cat_id is None:
                cat_id = list(CAT_MAP.values())[0]

            batch.append({
                "id": uuid.uuid4(),
                "title": fpath.stem[:500],
                "category_id": cat_id,
                "original_filename": fpath.name,
                "original_path": f"s3://{MINIO_BUCKET}/{obj_key}",
                "file_size": fpath.stat().st_size,
                "file_ext": fpath.suffix.lower().lstrip(".") or "none",
                "tags": tags,
                "uploader_id": ADMIN_ID,
            })
            ok += 1

            if len(batch) >= 200:
                await batch_insert(batch)
                batch = []
                pct = ok * 100 // len(all_files)
                print(f"  [{ok}/{len(all_files)}] ({pct}%)")

        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"  FAIL: {fpath.name}: {e}")

    if batch:
        await batch_insert(batch)

    print(f"\nDONE: {ok} imported, {fail} failed")
    total_docs = ok + fail
    print(f"Check: http://192.168.60.175:8000/api/documents?page=1&size=1")

asyncio.run(main())
