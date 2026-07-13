#!/usr/bin/env python3
"""
迈瑞生知识库 — 超高速批量导入 (直写 MinIO + 批量注册 DB)
绕过 FastAPI UploadFile 瓶颈, 直接:
  1. 并发上传文件到 MinIO (20 workers)
  2. 批量调用 API 注册文档元数据 (不传文件, 只传元数据)

预计速度: ~10-20 文件/秒 (vs 之前的 0.5/秒)
"""
import requests, json, os, sys, time, boto3, uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from io import BytesIO

API = "http://192.168.60.175:8000/api"
BASE = Path("D:/知识库/迈瑞生知识库")

# MinIO config (same as server .env)
MINIO_ENDPOINT = "192.168.60.175:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"
MINIO_BUCKET = "marweis-documents"
MINIO_SECURE = False

WORKERS = 16  # 并发上传 workers
DB_BATCH = 50  # 每50个文件批量提交一次元数据

# State
token = None
headers = {}
cat_cache = {}
cat_lock = Lock()
stats_lock = Lock()
stats = {"ok": 0, "fail": 0, "total": 0}
db_queue = []  # 待注册的文档元数据
db_lock = Lock()

def login():
    global token, headers
    r = requests.post(f"{API}/auth/login",
        json={"username": "admin", "password": "marweis2026"})
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"[OK] Login")

def load_cats():
    global cat_cache
    r = requests.get(f"{API}/categories", headers=headers)
    def walk(nodes, path=""):
        for n in nodes:
            full = f"{path}/{n['name']}" if path else n["name"]
            cat_cache[n["name"]] = n["id"]
            cat_cache[full] = n["id"]
            walk(n.get("children", []), full)
    walk(r.json())
    print(f"[OK] {len(cat_cache)} categories loaded")

def ensure_cat(name, parent_name=None):
    """Thread-safe category creation"""
    if name in cat_cache:
        return cat_cache[name]
    with cat_lock:
        if name in cat_cache:
            return cat_cache[name]
        parent_id = ensure_cat(parent_name) if parent_name else None
        r = requests.post(f"{API}/categories", headers=headers, json={
            "name": name, "parent_id": parent_id, "sort_order": 0
        })
        if r.status_code == 200:
            cat_cache[name] = r.json()["id"]
            print(f"\n  [CAT] {name}")
            return cat_cache[name]
        return None

# ---- MinIO direct upload ----

def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET,
    )

def ensure_bucket(s3):
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except:
        s3.create_bucket(Bucket=MINIO_BUCKET)

def upload_to_minio(filepath, s3_client):
    """Upload file directly to MinIO, return object metadata"""
    ext = filepath.suffix.lower().lstrip('.')
    obj_key = f"originals/{uuid.uuid4()}/{filepath.name}"

    with open(filepath, "rb") as f:
        s3_client.upload_fileobj(f, MINIO_BUCKET, obj_key)

    return {
        "original_path": f"s3://{MINIO_BUCKET}/{obj_key}",
        "file_size": filepath.stat().st_size,
        "file_ext": ext,
        "mime_type": "application/octet-stream",
        "original_filename": filepath.name,
    }

# ---- DB registration (batch) ----

def flush_db_batch():
    """Register multiple documents at once via a single bulk API concept
    Since we don't have a true bulk endpoint, we do concurrent single-doc POSTs
    but without file upload — just metadata pointing to MinIO objects.
    """
    global db_queue
    with db_lock:
        if not db_queue:
            return
        batch = db_queue[:]
        db_queue = []

    # Concurrently register metadata (no file upload = much faster)
    def register_one(item):
        try:
            r = requests.post(f"{API}/documents", headers=headers, json={
                "title": item["title"],
                "category_id": item["category_id"],
                "tags": json.dumps(item.get("tags", [])),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "source_url": f"s3://{MINIO_BUCKET}/{item['object_key']}",
            })
            if r.status_code == 200:
                with stats_lock:
                    stats["ok"] += 1
                return True
            else:
                with stats_lock:
                    stats["fail"] += 1
                return False
        except Exception as e:
            with stats_lock:
                stats["fail"] += 1
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(register_one, batch))


def make_tasks():
    """Generate all tasks: (filepath, title, cat_id, tags)"""
    tasks = []
    cat_nmpa = cat_cache["NMPA 法规库"]

    # 01-04, 07 flat dirs
    for dname, cats, tags in [
        ("01 分类目录", [ensure_cat("分类目录", "NMPA 法规库") or cat_nmpa], ["分类目录"]),
        ("02 豁免临床评价目录", [cat_nmpa], ["豁免临床评价"]),
        ("03 临床路径、指导原则", [cat_nmpa], ["临床路径"]),
        ("04 同产品查找", [cat_cache["公共知识区"]], ["产品库"]),
    ]:
        d = BASE / dname
        if d.exists():
            for f in d.iterdir():
                if f.is_file() and not f.name.startswith("~$"):
                    tasks.append((f, f.stem, cats[0], tags))

    # 07 法规
    reg_dir = BASE / "07 法规"
    if reg_dir.exists():
        for f in reg_dir.glob("*.pdf"):
            title = f.stem
            if "FDA" in title or "21 CFR" in title:
                c = cat_cache.get("FDA 法规库") or cat_nmpa
                t = ["法规", "FDA"]
            elif "EU" in title or "MDR" in title or "IVDR" in title:
                c = cat_cache.get("CE MDR 法规库") or cat_nmpa
                t = ["法规", "CE MDR"]
            else:
                c = cat_nmpa
                t = ["法规", "NMPA"]
            tasks.append((f, title, c, t))

    # 06 指导原则
    guide_cat = ensure_cat("指导原则", "NMPA 法规库") or cat_nmpa
    # IVD
    ivd_guide = ensure_cat("IVD指导原则", "指导原则") or guide_cat
    ivd_g_dir = BASE / "06 指导原则" / "体外诊断试剂"
    if ivd_g_dir.exists():
        for f in ivd_g_dir.glob("*.docx"):
            tasks.append((f, f.stem, ivd_guide, ["指导原则", "体外诊断试剂"]))
    # Med devices
    med_guide = ensure_cat("医疗器械指导原则", "指导原则") or guide_cat
    med_g_dir = BASE / "06 指导原则" / "医疗器械"
    if med_g_dir.exists():
        for sub in sorted(med_g_dir.iterdir()):
            if not sub.is_dir(): continue
            sc = ensure_cat(sub.name, "医疗器械指导原则") or med_guide
            for f in sub.glob("*.docx"):
                tasks.append((f, f.stem, sc, ["指导原则", "医疗器械"]))

    # 05 审评报告
    review_cat = ensure_cat("审评报告", "NMPA 法规库") or cat_nmpa
    # IVD
    ivd_review = ensure_cat("体外诊断试剂审评报告", "审评报告") or review_cat
    ivd_r_dir = BASE / "05 审评报告" / "体外诊断试剂"
    if ivd_r_dir.exists():
        for f in ivd_r_dir.glob("*.pdf"):
            parts = f.stem.rsplit("-", 2)
            title = parts[0] if len(parts) == 3 else f.stem
            tasks.append((f, title, ivd_review, ["审评报告", "体外诊断试剂"]))
    # Med devices
    med_review = ensure_cat("医疗器械审评报告", "审评报告") or review_cat
    med_r_dir = BASE / "05 审评报告" / "医疗器械"
    if med_r_dir.exists():
        for sub in sorted(med_r_dir.iterdir()):
            if not sub.is_dir(): continue
            sc = ensure_cat(sub.name, "医疗器械审评报告") or med_review
            for f in sub.glob("*.pdf"):
                parts = f.stem.rsplit("-", 2)
                title = parts[0] if len(parts) == 3 else f.stem
                tasks.append((f, title, sc, ["审评报告", "医疗器械"]))

    return tasks


def main():
    print("=" * 60)
    print("  迈瑞生知识库 — 超高速导入 (直写 MinIO)")
    print("=" * 60)

    login()
    load_cats()

    # Init MinIO
    print("\n--- Init MinIO ---")
    s3 = get_minio_client()
    ensure_bucket(s3)
    print(f"[OK] MinIO connected, bucket '{MINIO_BUCKET}' ready")

    # Generate tasks
    print("\n--- Building task list ---")
    tasks = make_tasks()
    stats["total"] = len(tasks)
    print(f"  Total: {len(tasks)} files")

    # Phase 1: Upload all files to MinIO (fast!)
    print(f"\n--- Phase 1: Upload to MinIO ({WORKERS} workers) ---")
    t0 = time.time()
    completed = []

    def upload_task(fp, title, cat_id, tags):
        try:
            meta = upload_to_minio(fp, s3)
            return {
                "title": title,
                "category_id": cat_id,
                "tags": tags,
                "summary": "",
                "source": "",
                "object_key": meta["original_path"],
            }
        except Exception as e:
            print(f"\n  ! MinIO upload failed: {fp.name}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(upload_task, fp, title, cid, tags) for fp, title, cid, tags in tasks]

        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                completed.append(result)
            if (i+1) % 100 == 0 or i+1 == len(tasks):
                elapsed = time.time() - t0
                print(f"  [{i+1}/{len(tasks)}] MinIO uploads, {len(completed)} ok ({elapsed:.0f}s)")

    elapsed1 = time.time() - t0
    print(f"  Phase 1 done: {len(completed)} files in {elapsed1:.0f}s ({len(completed)/elapsed1:.1f}/s)")

    # Phase 2: Register metadata via API (fast - no file transfer)
    print(f"\n--- Phase 2: Register metadata ({len(completed)} docs) ---")
    t0 = time.time()
    stats["ok"] = 0
    stats["fail"] = 0

    def register_meta(item):
        try:
            r = requests.post(f"{API}/documents", headers=headers, json={
                "title": item["title"],
                "category_id": item["category_id"],
                "tags": json.dumps(item.get("tags", [])),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "source_url": item["object_key"],
            })
            if r.status_code == 200:
                with stats_lock:
                    stats["ok"] += 1
            else:
                with stats_lock:
                    stats["fail"] += 1
        except Exception:
            with stats_lock:
                stats["fail"] += 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(register_meta, item) for item in completed]
        for i, _ in enumerate(as_completed(futures)):
            if (i+1) % 200 == 0 or i+1 == len(completed):
                elapsed = time.time() - t0
                rate = (i+1) / elapsed if elapsed > 0 else 0
                print(f"  [{i+1}/{len(completed)}] metadata registered ({rate:.1f}/s)")

    elapsed2 = time.time() - t0
    total_elapsed = elapsed1 + elapsed2
    print(f"\n{'=' * 60}")
    print(f"  ALL DONE!")
    print(f"  Phase 1 (MinIO): {elapsed1:.0f}s ({len(completed)/elapsed1:.1f} files/s)")
    print(f"  Phase 2 (API):   {elapsed2:.0f}s ({len(completed)/elapsed2:.1f} docs/s)")
    print(f"  Total:           {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print(f"  Imported:        {stats['ok']} OK, {stats['fail']} FAIL")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
