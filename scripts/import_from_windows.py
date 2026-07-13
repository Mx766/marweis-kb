#!/usr/bin/env python3
"""
Windows 本地批量上传脚本
遍历 D:/知识库/迈瑞生知识库 目录，按目录结构分类，调用服务器 API 上传
"""
import requests, json, os, sys, time
from pathlib import Path

API = "http://192.168.60.175:8000/api"
BASE = Path("D:/知识库/迈瑞生知识库")

# Login
def login():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "marweis2026"})
    d = r.json()
    print(f"[OK] Login: {d['user']['display_name']}")
    return d["token"], {"Authorization": f"Bearer {d['token']}"}

# Category management
cat_cache = {}

def load_cats(h):
    """Get all category IDs"""
    global cat_cache
    r = requests.get(f"{API}/categories", headers=h)
    def walk(nodes, path=""):
        for n in nodes:
            full = f"{path}/{n['name']}" if path else n["name"]
            cat_cache[n["name"]] = n["id"]
            cat_cache[full] = n["id"]
            walk(n.get("children", []), full)
    walk(r.json())
    print(f"[OK] Loaded {len(cat_cache)} category entries")

def ensure_cat(name, parent_name, h):
    """Ensure category exists, create if not"""
    if name in cat_cache:
        return cat_cache[name]
    parent_id = ensure_cat(parent_name, None, h) if parent_name else None
    r = requests.post(f"{API}/categories", json={
        "name": name, "parent_id": parent_id, "sort_order": 0
    }, headers=h)
    if r.status_code == 200:
        cat_cache[name] = r.json()["id"]
        print(f"  [NEW] {name} -> {cat_cache[name]}")
        return cat_cache[name]
    print(f"  [FAIL] {name}: {r.text[:100]}")
    return None

def upload(filepath, title, cat_id, tags, h):
    """Upload single file"""
    with open(filepath, "rb") as f:
        data = {
            "title": title[:500],
            "category_id": cat_id,
            "tags": json.dumps(tags),
            "summary": "",
            "source": "",
        }
        files = {"file": (filepath.name, f, "application/octet-stream")}
        return requests.post(f"{API}/documents", data=data, files=files, headers=h)

# ---- IMPORTERS ----

def import_flat(dirpath, cat_name, tags, h):
    """Import flat directory (no subdirs)"""
    results = []
    for f in dirpath.iterdir():
        if not f.is_file() or f.name.startswith("~$"):
            continue
        title = f.stem
        try:
            r = upload(f, title, cat_cache.get(cat_name), tags, h)
            if r.status_code == 200:
                results.append((f.name, True, r.json()["id"]))
            else:
                results.append((f.name, False, f"HTTP {r.status_code}: {r.text[:100]}"))
        except Exception as e:
            results.append((f.name, False, str(e)[:100]))
    return results

def import_review_reports(basepath, h):
    """05 审评报告"""
    results = []
    # Ensure parent categories
    nmpa = cat_cache["NMPA 法规库"]
    review = ensure_cat("审评报告", "NMPA 法规库", h) or nmpa
    med_dev = ensure_cat("医疗器械审评报告", "审评报告", h) or review
    ivd_cat = ensure_cat("体外诊断试剂审评报告", "审评报告", h) or review

    # IVD reports
    ivd_dir = basepath / "体外诊断试剂"
    if ivd_dir.exists():
        pdfs = [f for f in ivd_dir.glob("*.pdf")]
        print(f"  [IVD] {len(pdfs)} files")
        for i, f in enumerate(pdfs):
            if i > 0 and i % 50 == 0: print(f"    {i}/{len(pdfs)}")
            parts = f.stem.rsplit("-", 2)
            title = parts[0] if len(parts) == 3 else f.stem
            try:
                r = upload(f, title, ivd_cat, ["审评报告", "体外诊断试剂"], h)
                results.append((f.name, r.status_code == 200, r.json().get("id", "") if r.status_code == 200 else ""))
            except Exception as e:
                results.append((f.name, False, str(e)[:100]))

    # Medical devices
    med_dir = basepath / "医疗器械"
    if med_dir.exists():
        for sub in sorted(med_dir.iterdir()):
            if not sub.is_dir():
                continue
            sub_name = sub.name
            sub_cat = ensure_cat(sub_name, "医疗器械审评报告", h) or med_dev
            pdfs = [f for f in sub.glob("*.pdf")]
            if not pdfs:
                continue
            print(f"  [{sub_name}] {len(pdfs)} files")
            for f in pdfs:
                parts = f.stem.rsplit("-", 2)
                title = parts[0] if len(parts) == 3 else f.stem
                try:
                    r = upload(f, title, sub_cat, ["审评报告", "医疗器械"], h)
                    results.append((f.name, r.status_code == 200, r.json().get("id", "") if r.status_code == 200 else ""))
                except Exception as e:
                    results.append((f.name, False, str(e)[:100]))
    return results

def import_guidelines(basepath, h):
    """06 指导原则"""
    results = []
    nmpa = cat_cache["NMPA 法规库"]
    guide = ensure_cat("指导原则", "NMPA 法规库", h) or nmpa
    med_guide = ensure_cat("医疗器械指导原则", "指导原则", h) or guide
    ivd_guide = ensure_cat("IVD指导原则", "指导原则", h) or guide

    # IVD
    ivd_dir = basepath / "体外诊断试剂"
    if ivd_dir.exists():
        docs = [f for f in ivd_dir.glob("*.docx")]
        print(f"  [IVD] {len(docs)} files")
        for i, f in enumerate(docs):
            if i > 0 and i % 50 == 0: print(f"    {i}/{len(docs)}")
            try:
                r = upload(f, f.stem, ivd_guide, ["指导原则", "体外诊断试剂"], h)
                results.append((f.name, r.status_code == 200, r.json().get("id", "") if r.status_code == 200 else ""))
            except Exception as e:
                results.append((f.name, False, str(e)[:100]))

    # Medical devices
    med_dir = basepath / "医疗器械"
    if med_dir.exists():
        for sub in sorted(med_dir.iterdir()):
            if not sub.is_dir():
                continue
            sub_name = sub.name
            sub_cat = ensure_cat(sub_name, "医疗器械指导原则", h) or med_guide
            docs = [f for f in sub.glob("*.docx")]
            if not docs:
                continue
            print(f"  [{sub_name}] {len(docs)} files")
            for f in docs:
                try:
                    r = upload(f, f.stem, sub_cat, ["指导原则", "医疗器械"], h)
                    results.append((f.name, r.status_code == 200, r.json().get("id", "") if r.status_code == 200 else ""))
                except Exception as e:
                    results.append((f.name, False, str(e)[:100]))
    return results


def main():
    print("=" * 60)
    print("  迈瑞生知识库 — Windows 批量导入")
    print("=" * 60)

    token, h = login()
    load_cats(h)

    # Ensure metadata categories
    print("\n--- Ensuring categories ---")
    nmpa_id = cat_cache.get("NMPA 法规库") or cat_cache.get("公共知识区")
    for name, parent in [
        ("审评报告", "NMPA 法规库"),
        ("指导原则", "NMPA 法规库"),
    ]:
        ensure_cat(name, parent, h)

    total_ok = 0
    total_fail = 0

    # Import order: small dirs first, then large ones
    tasks = [
        ("01 分类目录",      lambda: import_flat(BASE/"01 分类目录", "NMPA 法规库", ["分类目录"], h)),
        ("02 豁免临床评价目录", lambda: import_flat(BASE/"02 豁免临床评价目录", "NMPA 法规库", ["豁免临床评价"], h)),
        ("03 临床路径、指导原则", lambda: import_flat(BASE/"03 临床路径、指导原则", "NMPA 法规库", ["临床路径"], h)),
        ("04 同产品查找",     lambda: import_flat(BASE/"04 同产品查找", "公共知识区", ["产品库"], h)),
        ("07 法规",          lambda: import_flat(BASE/"07 法规", "NMPA 法规库", ["法规"], h)),
        ("06 指导原则",      lambda: import_guidelines(BASE/"06 指导原则", h)),
        ("05 审评报告",      lambda: import_review_reports(BASE/"05 审评报告", h)),
    ]

    for name, fn in tasks:
        d = BASE / name
        if not d.exists():
            print(f"[SKIP] {name}")
            continue
        print(f"\n--- [{name}] ---")
        t0 = time.time()
        res = fn()
        ok = sum(1 for _, succ, _ in res if succ)
        fail = sum(1 for _, succ, _ in res if not succ)
        total_ok += ok
        total_fail += fail
        elapsed = time.time() - t0
        print(f"  => {ok} OK, {fail} FAIL ({elapsed:.0f}s)")

    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {total_ok} OK, {total_fail} FAIL")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
