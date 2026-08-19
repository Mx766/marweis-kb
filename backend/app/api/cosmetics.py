"""Cosmetics ingredient search API — dedicated search engine for ingredients."""
import re
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_optional
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.permissions import PermissionService

router = APIRouter(prefix="/api/cosmetics", tags=["cosmetics"])


@router.get("/ingredient-search")
async def ingredient_search(
    q: str = Query(..., min_length=1, description="原料名称（中/英/INCI/韩文）"),
    mode: str = Query("fuzzy", description="搜索模式: fuzzy | exact | batch"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Dedicated cosmetics ingredient search engine.

    - Searches CIR safety reports (content_text) for ingredient names
    - Searches KCIA dictionary (content_text) for Korean/English names
    - Returns structured results with ingredient context

    Batch mode: split q by comma/newline, search each term independently.
    """
    results: list[dict] = []
    total = 0

    # Determine search terms
    if mode == "batch":
        terms = [t.strip() for t in re.split(r'[,，\n\r]+', q) if t.strip()]
        if not terms:
            return {"items": [], "total": 0, "query": q, "mode": mode}
    else:
        terms = [q.strip()]

    # Permission: get visible categories
    allowed_cat_ids: list | None = None
    if current_user and current_user.role != "super_admin":
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        allowed_cat_ids = [str(v) for v in visible]
        if not allowed_cat_ids:
            return {"items": [], "total": 0, "query": q, "mode": mode}

    # ── Find cosmetics-relevant categories ──
    # Include all ingredient-related data sources for comprehensive search
    cosmetics_cats = await db.execute(
        select(Category).where(
            or_(
                Category.name == "美国化妆品成分查询（CIR）",
                Category.name == "内部成分审核",
                Category.name == "已使用化妆品原料目录",
            )
        )
    )
    target_cat_ids = [c.id for c in cosmetics_cats.scalars().all()]
    if not target_cat_ids:
        return {"items": [], "total": 0, "query": q, "mode": mode}

    # Apply permission filter
    if allowed_cat_ids is not None:
        target_cat_ids = [cid for cid in target_cat_ids if str(cid) in allowed_cat_ids]

    all_matches: list[dict] = []

    for term in terms:
        pattern = f"%{term}%"

        # Always search both with and without spaces
        # e.g., "EDTA二钠" matches "EDTA 二钠" in the content
        conditions = [
            Document.is_deleted == False,
            Document.category_id.in_(target_cat_ids),
            or_(
                Document.content_text.ilike(pattern),
                func.replace(func.replace(Document.content_text, " ", ""), "　", "").ilike(pattern),
            ),
        ]

        query_obj = (
            select(Document)
            .where(*conditions)
            .order_by(Document.updated_at.desc())
        )

        docs_result = await db.execute(query_obj)
        docs = docs_result.scalars().all()

        for doc in docs:
            # Extract matching lines from content_text
            content = doc.content_text or ""
            matches = _extract_matches(content, term, mode)
            for m in matches:
                all_matches.append({
                    "search_term": term,
                    "match_type": "exact" if mode == "exact" else "fuzzy",
                    "ingredient_name": m["name"],
                    "inci_name": m.get("inci", ""),
                    "korean_name": m.get("korean", ""),
                    "report_title": doc.title,
                    "report_summary": doc.summary or "",
                    "document_id": str(doc.id),
                    "category_id": str(doc.category_id) if doc.category_id else "",
                    "source": _detect_source(doc.title),
                    "match_context": m["context"],
                })

    # Deduplicate: same ingredient + same report
    seen = set()
    unique_matches = []
    for m in all_matches:
        key = (m["ingredient_name"].lower(), m["report_title"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    total = len(unique_matches)

    # Paginate
    start = (page - 1) * size
    end = start + size
    paginated = unique_matches[start:end]

    return {
        "items": paginated,
        "total": total,
        "query": q,
        "mode": mode,
        "page": page,
        "size": size,
    }


def _contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[一-鿿]', text))


def _is_whole_word(text: str, term_lower: str) -> bool:
    """Check if term appears as a whole word within text.
    Word boundaries: start/end of string, spaces, hyphens, commas, slashes, parentheses, pipes.
    For Chinese text: any match counts (Chinese doesn't use word delimiters)."""
    if not text or not term_lower:
        return False
    idx = text.lower().find(term_lower)
    if idx < 0:
        return False
    # Chinese text: accept any substring match
    if _contains_chinese(text) or _contains_chinese(term_lower):
        return True
    # Check left boundary
    if idx > 0 and text[idx - 1] not in ' -/,()|':
        return False
    # Check right boundary
    end = idx + len(term_lower)
    if end < len(text) and text[end] not in ' -/,()|':
        return False
    return True


def _extract_matches(content: str, term: str, mode: str) -> list[dict]:
    """Extract ingredient matches from document content_text."""
    results = []
    term_lower = term.lower()
    is_exact = mode == "exact"

    # CIR content format:
    #   - IngredientName (INCI: InciName)
    # Chinese index format (pipe-delimited):
    #   idx | idx2 | 中文名 | ENGLISH_NAME | ...
    # KCIA content format:
    #   | 序号 | 韩文名 | 英文名 |

    lines = content.split('\n')

    for line in lines:
        line_lower = line.lower()
        # Space-insensitive match for fuzzy mode
        if is_exact:
            if term_lower not in line_lower:
                continue
        else:
            # Fuzzy: also match after stripping spaces (e.g., "EDTA二钠" matches "EDTA 二钠")
            if term_lower not in line_lower:
                term_stripped = term_lower.replace(" ", "").replace("　", "")
                line_stripped = line_lower.replace(" ", "").replace("　", "")
                if term_stripped not in line_stripped:
                    continue

        # Parse pipe-delimited Chinese index: idx | idx2 | 中文名 | ENGLISH
        # Match pipe-delimited formats:
        #   Leading pipe:  | idx | idx2 | Chinese | ENGLISH |  (KCIA)
        #   No leading pipe: idx | idx2 | Chinese | ENGLISH |  (Chinese index)
        pipe_match = re.match(r'\|?\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*([A-Z0-9][A-Za-z0-9\s\-_,;]+(?:\s*\([^)]*\))?)\s*\|?', line.strip())
        if pipe_match:
            chinese_name = pipe_match.group(3).strip()
            english_name = pipe_match.group(4).strip()
            # Exact mode: term must match as whole word within the name
            if is_exact:
                if not _is_whole_word(english_name, term_lower) and not _is_whole_word(chinese_name, term_lower):
                    continue
                display_name = english_name if _is_whole_word(english_name, term_lower) else chinese_name
            else:
                if term_lower in english_name.lower():
                    display_name = english_name
                else:
                    display_name = chinese_name
            results.append({
                "name": display_name,
                "inci": english_name if english_name != display_name else "",
                "korean": chinese_name if display_name != chinese_name else "",
                "context": f"{chinese_name} | {english_name}",
            })
            continue

        # Parse IECIC table format: | seq | 中文名 | INCI英文名 | 备注 |
        iecic_match = re.match(r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*([A-Z0-9][A-Za-z0-9\s\-_,;()/]+?)\s*\|', line.strip())
        if iecic_match:
            cn_name = iecic_match.group(2).strip()
            en_name = iecic_match.group(3).strip()
            if is_exact:
                if not _is_whole_word(cn_name, term_lower) and not _is_whole_word(en_name, term_lower):
                    continue
                display_name = cn_name if _is_whole_word(cn_name, term_lower) else en_name
            else:
                display_name = cn_name if term_lower in cn_name else en_name
            results.append({
                "name": display_name,
                "inci": en_name if en_name != display_name else "",
                "korean": cn_name if cn_name != display_name else "",
                "context": f"{cn_name} | {en_name}",
            })
            continue

        # Parse CIR ingredient line: "  - Name (INCI: InciName)"
        cir_match = re.match(r'\s*[-•*]\s*(.+?)(?:\s*\(INCI:\s*(.+?)\))?$', line.strip())
        if cir_match:
            ing_name = cir_match.group(1).strip()
            inci_name = (cir_match.group(2) or "").strip()
            # Exact mode: term must appear as a whole word within ingredient/INCI name
            if is_exact:
                if not _is_whole_word(ing_name, term_lower) and not _is_whole_word(inci_name, term_lower):
                    continue
            results.append({
                "name": ing_name,
                "inci": inci_name,
                "korean": "",
                "context": line.strip()[:200],
            })
            continue

        # Parse KCIA table line: "| num | korean | english |"
        kcia_match = re.match(r'\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|', line)
        if kcia_match:
            kor_name = kcia_match.group(1).strip()
            eng_name = kcia_match.group(2).strip()
            if is_exact:
                if not _is_whole_word(kor_name, term_lower) and not _is_whole_word(eng_name, term_lower):
                    continue
            results.append({
                "name": eng_name,
                "inci": "",
                "korean": kor_name,
                "context": line.strip()[:200],
            })
            continue

        # Generic match (skip in exact mode — only structured matches count)
        if is_exact:
            continue
        clean = line.strip().lstrip('-•*#| ')
        if clean and len(clean) > 2:
            results.append({
                "name": clean[:150],
                "inci": "",
                "korean": "",
                "context": clean[:200],
            })

    return results


def _detect_source(title: str) -> str:
    """Detect data source from document title."""
    if "KCIA" in title or "韩英" in title:
        return "KCIA"
    if "CIR" in title or "Safety Assessment" in title:
        return "CIR"
    return "未知"


@router.get("/knowledge-graph")
async def knowledge_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Generate knowledge graph data for the cosmetics department.
    Returns nodes (categories + document types) and links (relationships).
    """
    # Get cosmetics root
    root = (await db.execute(
        select(Category).where(Category.name == "8. 化妆品·医美部")
    )).scalar_one_or_none()
    if not root:
        return {"nodes": [], "links": []}

    # Get all descendants recursively
    all_cats = (await db.execute(select(Category.id, Category.name, Category.parent_id))).all()
    children_map: dict[str, list] = {}
    name_map = {}
    for cid, cname, cpid in all_cats:
        name_map[cid] = cname
        if cpid:
            children_map.setdefault(str(cpid), []).append((cid, cname))

    # Collect descendants of cosmetics root
    def get_descendants(pid):
        result = [(pid, name_map.get(pid, ""))]
        for cid, cname in children_map.get(str(pid), []):
            result.extend(get_descendants(cid))
        return result

    all_ids = get_descendants(root.id)
    all_id_set = {cid for cid, _ in all_ids}

    # 权限过滤：只返回当前用户可见分类（与分类列表接口一致）
    if not (current_user and current_user.role == "super_admin"):
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        visible_set = set(visible)
        all_ids = [(cid, cname) for cid, cname in all_ids if cid in visible_set]
        all_id_set = {cid for cid, _ in all_ids}

    nodes = []
    links = []
    seen = set()

    # Color palette
    colors = [
        "#1e50ae", "#2e86c1", "#27ae60", "#8e44ad", "#e74c3c",
        "#f39c12", "#16a085", "#2980b9", "#c0392b", "#7f8c8d",
    ]

    # Build category nodes
    for cid, cname in all_ids:
        if cid not in all_id_set:
            continue
        # Count docs in this category
        doc_count = (await db.execute(
            select(func.count(Document.id)).where(
                Document.category_id == cid, Document.is_deleted == False
            )
        )).scalar()

        # Symbol size based on doc count
        symbol_size = max(20, min(80, 15 + doc_count * 0.5)) if doc_count > 0 else 15

        # Category name for display
        label = cname.replace("8. ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "").replace("4. ", "").replace("5. ", "")
        if len(label) > 8:
            label = label[:8] + ".."

        category_val = 0 if cid == root.id else 1

        nodes.append({
            "id": str(cid),
            "name": cname,
            "label": label,
            "symbolSize": symbol_size,
            "category": category_val,
            "value": doc_count,
        })

        # Link to parent via children_map
        for parent_cid_str, child_list in children_map.items():
            for child_id, _ in child_list:
                if child_id == cid:
                    links.append({
                        "source": parent_cid_str,
                        "target": str(cid),
                        "value": doc_count,
                    })

    # Add document type summary nodes linked to their categories
    type_labels = {
        "pdf": ("PDF文件", "#e74c3c"),
        "doc": ("Word文档", "#2980b9"),
        "xls": ("Excel表格", "#27ae60"),
        "link": ("法规链接", "#8e44ad"),
        "file": ("其他文件", "#95a5a6"),
    }

    # Aggregate doc types per category
    cat_types = await db.execute(
        select(Document.category_id, Document.file_type, func.count(Document.id))
        .where(Document.category_id.in_([cid for cid, _ in all_ids if cid != root.id]), Document.is_deleted == False)
        .group_by(Document.category_id, Document.file_type)
    )
    for cid, ft, cnt in cat_types.all():
        if cnt < 3:  # Only show significant clusters
            continue
        if ft not in type_labels:
            continue
        tlabel, tcolor = type_labels[ft]
        node_id = f"type_{cid}_{ft}"
        cat_name = name_map.get(cid, "")[:12]
        nodes.append({
            "id": node_id,
            "name": f"{tlabel}",
            "label": f"{tlabel}({cnt})",
            "symbolSize": max(12, min(40, 8 + cnt)),
            "category": 2,
            "value": cnt,
            "itemStyle": {"color": tcolor},
        })
        links.append({
            "source": str(cid),
            "target": node_id,
            "value": cnt,
        })

    # Add top-level 临床研究部ss-references between section parents
    section_parents = ["1. 法规与标准", "2. 化妆品原料", "3. 标签与技术要求", "4. 审核与项目", "5. 国际资源"]
    section_ids = [cid for cid, cname in all_ids if cname in section_parents]
    for i in range(len(section_ids)):
        for j in range(i + 1, len(section_ids)):
            # Calculate shared doc types as connection weight
            si = section_ids[i]
            sj = section_ids[j]
            links.append({
                "source": str(si),
                "target": str(sj),
                "value": 3,
                "lineStyle": {"type": "dashed", "opacity": 0.5},
            })

    return {
        "nodes": nodes,
        "links": links,
        "categories": [
            {"name": "根节点"},
            {"name": "分类"},
            {"name": "文档类型"},
        ],
    }
