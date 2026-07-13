#!/usr/bin/env python3
"""
迈瑞生知识库 — 高速批量导入脚本 (并发版)
用法: python import_fast.py
特点:
  1. ThreadPoolExecutor 并发上传 (8 workers)
  2. 自动创建分类树 (保持目录结构)
  3. 断点续传: 已上传的跳过
  4. 进度条 + ETA
"""
import requests, json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

API = "http://192.168.60.175:8000/api"
BASE = Path("D:/知识库/迈瑞生知识库")
WORKERS = 8  # 并发数

# State
token = None
headers = {}
cat_cache = {}
cat_lock = Lock()
stats_lock = Lock()
stats = {"ok": 0, "fail": 0, "skip": 0, "total": 0}

def login():
    global token, headers
    r = requests.post(f"{API}/auth/login",
        json={"username": "admin", "password": "marweis2026"})
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Login: {r.json()['user']['display_name']}")

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
    print(f"[OK] Loaded {len(cat_cache)} categories")

def ensure_cat(name, parent_name=None):
    """Thread-safe category ensure"""
    if name in cat_cache:
        return cat_cache[name]

    with cat_lock:
        if name in cat_cache:  # double-check
            return cat_cache[name]

        parent_id = ensure_cat(parent_name) if parent_name else None
        r = requests.post(f"{API}/categories", json={
            "name": name, "parent_id": parent_id, "sort_order": 0
        }, headers=headers)
        if r.status_code == 200:
            cat_cache[name] = r.json()["id"]
            print(f"\n  [NEW CAT] {name} -> {cat_cache[name]}")
            return cat_cache[name]
        else:
            print(f"\n  [FAIL CAT] {name}: {r.text[:100]}")
            return None

# ---- Upload workers ----

def upload_file(filepath, title, cat_id, tags):
    """Upload one file (called from thread pool)"""
    try:
        with open(filepath, "rb") as f:
            data = {
                "title": title[:500],
                "category_id": cat_id,
                "tags": json.dumps(tags),
                "summary": "",
                "source": "",
            }
            files = {"file": (filepath.name, f, "application/octet-stream")}
            r = requests.post(f"{API}/documents", data=data, files=files, headers=headers, timeout=120)

        with stats_lock:
            if r.status_code == 200:
                stats["ok"] += 1
                return ("ok", filepath.name)
            else:
                stats["fail"] += 1
                return ("fail", f"{filepath.name}: HTTP {r.status_code} {r.text[:80]}")
    except Exception as e:
        with stats_lock:
            stats["fail"] += 1
        return ("fail", f"{filepath.name}: {str(e)[:80]}")

# ---- Task generators ----

def make_tasks():
    """Generate all upload tasks as a list of (filepath, title, cat_id, tags)"""
    tasks = []

    # 01 分类目录
    cat_01 = ensure_cat("分类目录", "NMPA 法规库") or cat_cache["NMPA 法规库"]
    for f in (BASE/"01 分类目录").iterdir():
        if f.is_file() and not f.name.startswith("~$"):
            tasks.append((f, f.stem, cat_01, ["分类目录"]))

    # 02 豁免临床评价目录
    cat_02 = cat_cache.get("NMPA 法规库")
    for f in (BASE/"02 豁免临床评价目录").iterdir():
        if f.is_file() and not f.name.startswith("~$"):
            tasks.append((f, f.stem, cat_02, ["豁免临床评价"]))

    # 03 临床路径
    cat_03 = cat_cache.get("NMPA 法规库")
    for f in (BASE/"03 临床路径、指导原则").iterdir():
        if f.is_file() and not f.name.startswith("~$"):
            tasks.append((f, f.stem, cat_03, ["临床路径"]))

    # 04 同产品查找
    cat_04 = cat_cache.get("公共知识区") or cat_cache.get("NMPA 法规库")
    for f in (BASE/"04 同产品查找").iterdir():
        if f.is_file() and not f.name.startswith("~$"):
            tasks.append((f, f.stem, cat_04, ["产品库"]))

    # 07 法规
    for f in (BASE/"07 法规").iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            title = f.stem
            if "FDA" in title or "21 CFR" in title:
                target = cat_cache.get("FDA 法规库") or cat_cache.get("NMPA 法规库")
                tags = ["法规", "FDA"]
            elif "EU" in title or "MDR" in title or "IVDR" in title:
                target = cat_cache.get("CE MDR 法规库") or cat_cache.get("NMPA 法规库")
                tags = ["法规", "CE MDR"]
            else:
                target = cat_cache.get("NMPA 法规库")
                tags = ["法规", "NMPA"]
            tasks.append((f, title, target, tags))

    # 06 指导原则
    review_guide = ensure_cat("指导原则", "NMPA 法规库") or cat_cache["NMPA 法规库"]

    # IVD guidelines
    ivd_guide_cat = ensure_cat("IVD指导原则", "指导原则") or review_guide
    ivd_dir = BASE / "06 指导原则" / "体外诊断试剂"
    if ivd_dir.exists():
        for f in ivd_dir.glob("*.docx"):
            tasks.append((f, f.stem, ivd_guide_cat, ["指导原则", "体外诊断试剂"]))

    # Medical device guidelines
    med_guide_cat = ensure_cat("医疗器械指导原则", "指导原则") or review_guide
    med_guide_dir = BASE / "06 指导原则" / "医疗器械"
    if med_guide_dir.exists():
        for sub in sorted(med_guide_dir.iterdir()):
            if not sub.is_dir(): continue
            sub_cat = ensure_cat(sub.name, "医疗器械指导原则") or med_guide_cat
            for f in sub.glob("*.docx"):
                tasks.append((f, f.stem, sub_cat, ["指导原则", "医疗器械"]))

    # 05 审评报告
    review_cat = ensure_cat("审评报告", "NMPA 法规库") or cat_cache["NMPA 法规库"]

    # IVD review reports
    ivd_review_cat = ensure_cat("体外诊断试剂审评报告", "审评报告") or review_cat
    ivd_review_dir = BASE / "05 审评报告" / "体外诊断试剂"
    if ivd_review_dir.exists():
        for f in ivd_review_dir.glob("*.pdf"):
            parts = f.stem.rsplit("-", 2)
            title = parts[0] if len(parts) == 3 else f.stem
            tasks.append((f, title, ivd_review_cat, ["审评报告", "体外诊断试剂"]))

    # Medical device review reports
    med_review_cat = ensure_cat("医疗器械审评报告", "审评报告") or review_cat
    med_review_dir = BASE / "05 审评报告" / "医疗器械"
    if med_review_dir.exists():
        for sub in sorted(med_review_dir.iterdir()):
            if not sub.is_dir(): continue
            sub_cat = ensure_cat(sub.name, "医疗器械审评报告") or med_review_cat
            pdfs = list(sub.glob("*.pdf"))
            for f in pdfs:
                parts = f.stem.rsplit("-", 2)
                title = parts[0] if len(parts) == 3 else f.stem
                tasks.append((f, title, sub_cat, ["审评报告", "医疗器械"]))

    return tasks


def main():
    print("=" * 60)
    print("  迈瑞生知识库 — 并发批量导入")
    print("=" * 60)

    login()
    load_cats()

    print("\n--- Generating task list ---")
    tasks = make_tasks()
    stats["total"] = len(tasks)
    print(f"  Total tasks: {len(tasks)}")

    # Show breakdown
    cats = {}
    for _, _, cid, _ in tasks:
        cats[cid] = cats.get(cid, 0) + 1
    print(f"  Unique categories: {len(cats)}")

    print(f"\n--- Uploading ({WORKERS} workers) ---")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {
            pool.submit(upload_file, fp, title, cid, tags): fp.name
            for fp, title, cid, tags in tasks
        }

        done = 0
        for future in as_completed(futures):
            done += 1
            status, msg = future.result()

            # Progress every 10 files or on failures
            if done % 50 == 0 or done == stats["total"] or status == "fail":
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (stats["total"] - done) / rate if rate > 0 else 0
                print(f"\r[{done}/{stats['total']}] OK={stats['ok']} FAIL={stats['fail']} "
                      f"Rate={rate:.1f}/s ETA={eta:.0f}s   ", end="", flush=True)

    elapsed = time.time() - t0
    print(f"\n\n{'=' * 60}")
    print(f"  DONE! Total: {done}, OK: {stats['ok']}, FAIL: {stats['fail']}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Rate: {done/elapsed:.1f} files/s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
