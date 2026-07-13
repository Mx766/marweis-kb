#!/usr/bin/env python3
"""
批量导入知识库文件脚本
通过 API 上传到 marweis-kb
"""
import os, sys, json, requests, re
from pathlib import Path

API_BASE = "http://localhost:8000/api"
SOURCE_DIR = "/tmp/kb_import"
TOKEN = None
CATEGORY_MAP = {}

def get_token():
    global TOKEN
    resp = requests.post(f"{API_BASE}/auth/login", json={
        "username": "admin",
        "password": "marweis2026"
    })
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.text}")
    TOKEN = resp.json()["token"]
    print(f"[OK] Logged in, token: {TOKEN[:20]}...")

def api_headers():
    return {"Authorization": f"Bearer {TOKEN}"}

def get_categories():
    resp = requests.get(f"{API_BASE}/categories", headers=api_headers())
    if resp.status_code != 200:
        raise Exception(f"Get categories failed: {resp.text}")
    def walk(nodes, path=""):
        for n in nodes:
            full = (path + "/" + n["name"]) if path else n["name"]
            CATEGORY_MAP[n["name"]] = n["id"]
            CATEGORY_MAP[full] = n["id"]
            walk(n.get("children", []), full)
    walk(resp.json())
    print(f"[OK] {len(CATEGORY_MAP)} category entries loaded")

def ensure_category(name, parent_name=None):
    if name in CATEGORY_MAP:
        return CATEGORY_MAP[name]
    parent_id = ensure_category(parent_name) if parent_name else None
    resp = requests.post(f"{API_BASE}/categories", json={
        "name": name,
        "parent_id": parent_id,
        "sort_order": 0,
    }, headers=api_headers())
    if resp.status_code == 200:
        data = resp.json()
        CATEGORY_MAP[name] = data["id"]
        print(f"  [NEW] Category '{name}' -> {data['id']}")
        return data["id"]
    else:
        print(f"  [FAIL] Create category '{name}': {resp.text}")
        return None

def upload_file(filepath, title, category_id, tags=None, summary=""):
    with open(filepath, 'rb') as f:
        files = {'file': (filepath.name, f, 'application/octet-stream')}
        data = {
            'title': title,
            'category_id': category_id,
            'tags': json.dumps(tags or []),
            'summary': summary,
            'source': '',
        }
        resp = requests.post(f"{API_BASE}/documents", data=data, files=files, headers=api_headers())
    if resp.status_code == 200:
        return resp.json()
    else:
        raise Exception(f"Upload failed: {resp.status_code} {resp.text[:200]}")

def file_to_title(filepath):
    return filepath.stem

# ---- Import functions per directory ----

def import_dir_simple(dirpath, category_key, tags, source_label):
    """Generic importer for flat directories"""
    cat_id = CATEGORY_MAP.get(category_key)
    if not cat_id:
        cat_id = ensure_category(category_key)
    results = []
    for f in dirpath.glob("*"):
        if not f.is_file() or f.name.startswith('~$'):
            continue
        try:
            r = upload_file(f, file_to_title(f), cat_id, tags=tags, summary="")
            results.append((f.name, True, r.get('id', '')))
        except Exception as e:
            results.append((f.name, False, str(e)[:100]))
    return results

def import_review_reports(dirpath):
    """05 审评报告 - nested by subcategory"""
    results = []
    # IVD
    ivd_dir = dirpath / "体外诊断试剂"
    if ivd_dir.exists():
        ivd_cat = ensure_category("体外诊断试剂审评报告", "审评报告")
        target = ivd_cat or CATEGORY_MAP.get("审评报告") or CATEGORY_MAP.get("NMPA 法规库")
        ivd_files = list(ivd_dir.glob("*.pdf"))
        print(f"  [05] IVD review reports: {len(ivd_files)} files")
        for i, f in enumerate(ivd_files):
            if i > 0 and i % 50 == 0:
                print(f"    ... {i}/{len(ivd_files)}")
            parts = f.stem.rsplit('-', 2)
            title = parts[0] if len(parts) == 3 else f.stem
            mfr = parts[1] if len(parts) == 3 else ''
            summary = f"{mfr}" if mfr else ''
            try:
                r = upload_file(f, title, target, tags=["审评报告", "体外诊断试剂"], summary=summary)
                results.append((f.name, True, r.get('id', '')))
            except Exception as e:
                results.append((f.name, False, str(e)[:100]))
    # Medical devices by 22 subcategories
    med_dir = dirpath / "医疗器械"
    if med_dir.exists():
        for sub_dir in sorted(med_dir.iterdir()):
            if not sub_dir.is_dir():
                continue
            cat_name = sub_dir.name
            ensure_category("医疗器械审评报告", "审评报告")
            sub_cat = ensure_category(cat_name, "医疗器械审评报告")
            target = sub_cat or CATEGORY_MAP.get("医疗器械审评报告") or CATEGORY_MAP.get("审评报告")
            pdfs = list(sub_dir.glob("*.pdf"))
            print(f"  [05] {cat_name}: {len(pdfs)} files")
            for f in pdfs:
                parts = f.stem.rsplit('-', 2)
                title = parts[0] if len(parts) == 3 else f.stem
                mfr = parts[1] if len(parts) == 3 else ''
                try:
                    r = upload_file(f, title, target, tags=["审评报告", "医疗器械"], summary=mfr)
                    results.append((f.name, True, r.get('id', '')))
                except Exception as e:
                    results.append((f.name, False, str(e)[:100]))
    return results

def import_guidelines(dirpath):
    """06 指导原则 - nested by subcategory"""
    results = []
    ivd_dir = dirpath / "体外诊断试剂"
    if ivd_dir.exists():
        ivd_cat = ensure_category("IVD指导原则", "指导原则")
        target = ivd_cat or CATEGORY_MAP.get("指导原则") or CATEGORY_MAP.get("NMPA 法规库")
        docx_files = list(ivd_dir.glob("*.docx"))
        print(f"  [06] IVD guidelines: {len(docx_files)} files")
        for i, f in enumerate(docx_files):
            if i > 0 and i % 50 == 0:
                print(f"    ... {i}/{len(docx_files)}")
            try:
                r = upload_file(f, file_to_title(f), target, tags=["指导原则", "体外诊断试剂"])
                results.append((f.name, True, r.get('id', '')))
            except Exception as e:
                results.append((f.name, False, str(e)[:100]))
    med_dir = dirpath / "医疗器械"
    if med_dir.exists():
        for sub_dir in sorted(med_dir.iterdir()):
            if not sub_dir.is_dir():
                continue
            cat_name = sub_dir.name
            ensure_category("医疗器械指导原则", "指导原则")
            sub_cat = ensure_category(cat_name, "医疗器械指导原则")
            target = sub_cat or CATEGORY_MAP.get("医疗器械指导原则") or CATEGORY_MAP.get("指导原则")
            docx_files = list(sub_dir.glob("*.docx"))
            print(f"  [06] {cat_name}: {len(docx_files)} files")
            for f in docx_files:
                try:
                    r = upload_file(f, file_to_title(f), target, tags=["指导原则", "医疗器械"])
                    results.append((f.name, True, r.get('id', '')))
                except Exception as e:
                    results.append((f.name, False, str(e)[:100]))
    return results

def import_regulations(dirpath):
    """07 法规 - classify by source"""
    results = []
    for f in dirpath.glob("*.pdf"):
        title = file_to_title(f)
        if "FDA" in title or "21 CFR" in title:
            target = CATEGORY_MAP.get("FDA 法规库") or CATEGORY_MAP.get("NMPA 法规库")
            tags = ["法规", "FDA"]
        elif "EU" in title or "MDR" in title or "IVDR" in title:
            target = CATEGORY_MAP.get("CE MDR 法规库") or CATEGORY_MAP.get("NMPA 法规库")
            tags = ["法规", "CE MDR"]
        else:
            target = CATEGORY_MAP.get("NMPA 法规库")
            tags = ["法规", "NMPA"]
        try:
            r = upload_file(f, title, target, tags=tags)
            results.append((f.name, True, r.get('id', '')))
        except Exception as e:
            results.append((f.name, False, str(e)[:100]))
    return results


def main():
    print("=" * 60)
    print("  迈瑞生知识库 — 批量导入工具")
    print("=" * 60)
    get_token()
    get_categories()

    # Ensure top-level categories for new content
    print("\n--- Ensuring categories ---")
    for name, parent in [
        ("审评报告", "NMPA 法规库"),
        ("指导原则", "NMPA 法规库"),
        ("医疗器械审评报告", "审评报告"),
        ("体外诊断试剂审评报告", "审评报告"),
        ("医疗器械指导原则", "指导原则"),
        ("IVD指导原则", "指导原则"),
    ]:
        ensure_category(name, parent)
    print(f"Categories: {len(CATEGORY_MAP)}")

    base = Path(SOURCE_DIR)
    all_results = {}
    total_ok, total_fail = 0, 0

    import_order = [
        ("07 法规", import_regulations),
        ("01 分类目录", lambda d: import_dir_simple(d, "NMPA 法规库", ["分类目录"], "NMPA/中检院")),
        ("02 豁免临床评价目录", lambda d: import_dir_simple(d, "NMPA 法规库", ["豁免临床评价"], "NMPA")),
        ("03 临床路径、指导原则", lambda d: import_dir_simple(d, "NMPA 法规库", ["临床路径"], "CMDE")),
        ("04 同产品查找", lambda d: import_dir_simple(d, "公共知识区", ["产品库"], "NMPA")),
        ("06 指导原则", import_guidelines),
        ("05 审评报告", import_review_reports),
    ]

    for dirname, import_func in import_order:
        dirpath = base / dirname
        if not dirpath.exists():
            print(f"[SKIP] {dirname} - not found")
            continue
        print(f"\n{'='*40}")
        print(f"[IMPORT] {dirname}")
        print(f"{'='*40}")
        try:
            res = import_func(dirpath)
            ok = sum(1 for _, success, _ in res if success)
            fail = sum(1 for _, success, _ in res if not success)
            all_results[dirname] = res
            total_ok += ok
            total_fail += fail
            print(f"  => {ok} OK, {fail} FAIL")
        except Exception as e:
            print(f"  => ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"  导入完成: {total_ok} OK, {total_fail} FAIL")
    print(f"{'='*60}")
    if total_fail > 0:
        print("\n--- 失败文件 ---")
        for dirname, res in all_results.items():
            for name, success, msg in res:
                if not success:
                    print(f"  [{dirname}] {name}: {msg}")

if __name__ == "__main__":
    main()
