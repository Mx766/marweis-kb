import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, cast, String, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.schemas import SearchResult
from app.permissions import PermissionService
from app.services.search_service import search_documents
from app.api.documents import _doc_to_item, _batch_load_uploaders
import uuid as _uuid

router = APIRouter()


async def _get_synonyms(db: AsyncSession, q: str) -> list[str]:
    """从同义词表扩展搜索词。先完整匹配，再子串匹配。支持双向查找。"""
    expanded = {q}
    terms_to_check = [q]
    for wlen in range(2, min(len(q) + 1, 6)):
        for i in range(len(q) - wlen + 1):
            term = q[i:i + wlen]
            if term not in terms_to_check:
                terms_to_check.append(term)

    for term in terms_to_check:
        try:
            # 正向：term → synonyms
            result = await db.execute(
                sa_text("SELECT synonyms FROM search_synonyms WHERE term = :t"),
                {"t": term}
            )
            row = result.fetchone()
            if row:
                for syn in row[0]:
                    expanded.add(syn)
            # 反向：term 是否是某词条的同义词
            result2 = await db.execute(
                sa_text("SELECT term, synonyms FROM search_synonyms WHERE :t = ANY(synonyms)"),
                {"t": term}
            )
            for row2 in result2.fetchall():
                expanded.add(row2[0])  # 加回主词条
                for syn in row2[1]:
                    expanded.add(syn)
        except Exception:
            pass

    if len(expanded) > 12:
        expanded = set(list(expanded)[:12])
    return list(expanded)


async def _content_search(
    db: AsyncSession,
    q: str,
    synonyms: list[str],
    allowed_cat_ids: list[str] | None,
    category_id: str | None = None,
    file_type: str | None = None,
    limit: int = 60,
) -> list[tuple[Document, float]]:
    """
    内容级搜索 + 关联度评分。

    先用原词做快速 ILIKE，再用同义词做补充搜索。
    评分 = 正文命中 + 标题命中 + 同义词命中 + trigram相似度
    """
    q_clean = q.strip()
    if len(q_clean) < 2:
        return []

    keyword = f"%{q_clean}%"

    # ── 公共过滤条件 ──
    def _build_cat_clause():
        clause = ""
        params = {}
        if category_id:
            clause += " AND d.category_id = :cat_id"
            params["cat_id"] = category_id
        if file_type:
            clause += " AND d.file_type ILIKE :ft"
            params["ft"] = f"{file_type}%"
        if allowed_cat_ids is not None and len(allowed_cat_ids) > 0:
            id_list = ",".join(f"'{cid}'" for cid in allowed_cat_ids)
            clause += f" AND d.category_id IN ({id_list})"
        return clause, params

    base_filter = (
        "d.is_deleted = false "
        "AND (d.file_type = 'link' OR d.source_url IS NULL OR d.source_url = '' "
        "OR NOT EXISTS ("
        "  SELECT 1 FROM documents l "
        "  WHERE l.file_type = 'link' AND l.is_deleted = false "
        "    AND l.source_url IS NOT NULL AND l.source_url <> '' "
        "    AND l.source_url = d.source_url AND l.id <> d.id"
        "))"
    )
    cat_clause, cat_params = _build_cat_clause()

    # ── 1. 主搜索：原词 ILIKE + trigram 相似度 ──
    main_sql = f"""
        SELECT d.id,
               (CASE WHEN d.title ILIKE :kw THEN 2.0 ELSE 0.0 END) +
               (CASE WHEN d.content_text ILIKE :kw THEN 3.0 ELSE 0.0 END) +
               COALESCE(similarity(d.title, :q), 0) * 1.5
               AS relevance
        FROM documents d
        WHERE {base_filter}
          {cat_clause}
          AND (d.content_text ILIKE :kw OR d.title ILIKE :kw)
        ORDER BY relevance DESC
        LIMIT :lim
    """
    params = {"q": q_clean, "kw": keyword, "lim": limit, **cat_params}

    try:
        result = await db.execute(sa_text(main_sql), params)
        scored_rows = [(row[0], float(row[1])) for row in result.fetchall()]
    except Exception:
        # 降级
        from sqlalchemy import or_
        conds = [Document.is_deleted == False]
        from sqlalchemy import exists
        from sqlalchemy.orm import aliased
        LinkDoc = aliased(Document)
        is_attachment = exists().where(
            LinkDoc.file_type == "link",
            LinkDoc.is_deleted == False,
            LinkDoc.source_url.isnot(None),
            LinkDoc.source_url != "",
            LinkDoc.source_url == Document.source_url,
            LinkDoc.id != Document.id,
        )
        conds.append(
            (Document.file_type == 'link') |
            (Document.source_url.is_(None)) |
            (Document.source_url == '') |
            (~is_attachment)
        )
        conds.append(Document.content_text.ilike(keyword) | Document.title.ilike(keyword))
        if category_id:
            conds.append(Document.category_id == _uuid.UUID(category_id))
        if file_type:
            conds.append(Document.file_type.ilike(f"{file_type}%"))
        if allowed_cat_ids is not None:
            conds.append(Document.category_id.in_([_uuid.UUID(c) for c in allowed_cat_ids]))
        query_obj = select(Document).where(*conds).order_by(Document.updated_at.desc()).limit(limit)
        r = await db.execute(query_obj)
        return [(d, 1.0) for d in r.scalars().all()]

    if not scored_rows:
        return []

    # 批量获取文档
    doc_ids = [row[0] for row in scored_rows]
    id_score_map = {str(row[0]): row[1] for row in scored_rows}
    docs_result = await db.execute(
        select(Document).where(Document.id.in_(doc_ids), Document.is_deleted == False)
    )
    docs = list(docs_result.scalars().all())
    scored = [(d, id_score_map.get(str(d.id), 0.0)) for d in docs]

    # ── 2. 同义词逐词搜索（并行，限制少量）──
    active_syns = [s for s in synonyms if s != q_clean][:5]
    if active_syns:
        syn_tasks = []
        for syn in active_syns:
            sk = f"%{syn}%"
            syn_sql = f"""
                SELECT d.id FROM documents d
                WHERE {base_filter} {cat_clause}
                  AND (d.content_text ILIKE :sk OR d.title ILIKE :sk)
                LIMIT 10
            """
            syn_tasks.append(db.execute(sa_text(syn_sql), {"sk": sk, **cat_params}))

        syn_results = await asyncio.gather(*syn_tasks, return_exceptions=True)
        syn_doc_ids: set[str] = set()
        for i, sr in enumerate(syn_results):
            if isinstance(sr, Exception):
                continue
            for row in sr.fetchall():
                syn_doc_ids.add(str(row[0]))

        # 同义词匹配到的文档（不在主搜索结果中），追加到结果
        existing_ids = {str(d.id) for d in docs}
        new_ids = syn_doc_ids - existing_ids
        if new_ids:
            new_id_uuids = [_uuid.UUID(nid) for nid in new_ids]
            new_result = await db.execute(
                select(Document).where(Document.id.in_(new_id_uuids), Document.is_deleted == False)
            )
            for d in new_result.scalars().all():
                scored.append((d, 0.5))  # 同义词匹配基础分

        # 同义词匹配的文档加分
        for i, (d, s) in enumerate(scored):
            if str(d.id) in syn_doc_ids:
                scored[i] = (d, s + 1.0)

    # 去重 + 排序
    seen: dict[str, tuple[Document, float]] = {}
    for d, s in scored:
        did = str(d.id)
        if did in seen:
            seen[did] = (d, max(seen[did][1], s))
        else:
            seen[did] = (d, s)
    final = sorted(seen.values(), key=lambda x: x[1], reverse=True)
    return final[:limit]


@router.get("")
async def search(
    q: str = Query("", min_length=0),
    category_id: str = Query(None),
    file_type: str = Query(None),
    tag: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # ── 权限过滤 ──
    allowed_cat_ids: list[str] | None = None
    if current_user is None:
        cats = await db.execute(select(Category))
        allowed_cat_ids = [str(c.id) for c in cats.scalars().all() if c.visible_departments is None]
    elif current_user.role != "super_admin":
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        allowed_cat_ids = [str(v) for v in visible]

    if allowed_cat_ids is not None and len(allowed_cat_ids) == 0:
        return SearchResult(items=[], total=0, query=q, page=page, size=size)

    async def _filter_results(docs):
        perm_svc = PermissionService(db, current_user)
        filtered = []
        for d in docs:
            if await perm_svc.can_view_document(d):
                filtered.append(d)
        return filtered

    def _snippet(text: str | None, query: str, length: int = 200) -> str:
        if not text or not query.strip():
            return ""
        idx = text.lower().find(query.strip().lower())
        if idx < 0:
            return text[:length]
        start = max(0, idx - 40)
        end = min(len(text), idx + length)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet

    # ── 无查询：返回最近文档 ──
    if not q.strip():
        conditions = [Document.is_deleted == False]
        from sqlalchemy import exists
        from sqlalchemy.orm import aliased
        LinkDoc = aliased(Document)
        is_attachment = exists().where(
            LinkDoc.file_type == "link",
            LinkDoc.is_deleted == False,
            LinkDoc.source_url.isnot(None),
            LinkDoc.source_url != "",
            LinkDoc.source_url == Document.source_url,
            LinkDoc.id != Document.id,
        )
        conditions.append(
            (Document.file_type == 'link') |
            (Document.source_url.is_(None)) |
            (Document.source_url == '') |
            (~is_attachment)
        )
        if category_id:
            conditions.append(Document.category_id == _uuid.UUID(category_id))
        if file_type:
            conditions.append(Document.file_type.ilike(f"{file_type}%"))
        if tag:
            conditions.append(cast(Document.tags, String).ilike(f"%{tag}%"))
        if allowed_cat_ids is not None:
            conditions.append(Document.category_id.in_([_uuid.UUID(c) for c in allowed_cat_ids]))

        count_query = select(func.count(Document.id)).where(*conditions)
        total = (await db.execute(count_query)).scalar()
        query_obj = (
            select(Document)
            .where(*conditions)
            .order_by(Document.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        docs = (await db.execute(query_obj)).scalars().all()
        docs = await _filter_results(docs)
        uploader_map = await _batch_load_uploaders(db, docs)
        items = [_doc_to_item(d, uploader_map.get(d.uploader_id)) for d in docs]
        return SearchResult(items=items, total=total, query=q, page=page, size=size)

    # ── 有查询：并行搜索 ──
    synonyms = await _get_synonyms(db, q)

    meili_task = search_documents(
        query=q, page=page, size=size,
        category_id=category_id, file_type=file_type,
        allowed_category_ids=allowed_cat_ids,
    )
    content_task = _content_search(
        db, q, synonyms, allowed_cat_ids,
        category_id=category_id, file_type=file_type,
        limit=size * 3,
    )

    meili_result, scored_docs = await asyncio.gather(meili_task, content_task)

    # ── 合并并排序 ──
    merged: dict[str, tuple[Document, float]] = {}

    if meili_result["hits"]:
        doc_ids = [_uuid.UUID(hit["id"]) for hit in meili_result["hits"]]
        docs_result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids), Document.is_deleted == False)
        )
        for i, d in enumerate(docs_result.scalars().all()):
            merged[str(d.id)] = (d, 4.0 - i * 0.1)

    for d, score in scored_docs:
        did = str(d.id)
        if did in merged:
            existing_doc, existing_score = merged[did]
            merged[did] = (existing_doc, existing_score + score)
        else:
            merged[did] = (d, score)

    sorted_docs = sorted(merged.values(), key=lambda x: x[1], reverse=True)
    merged_docs = [d for d, _ in sorted_docs]
    merged_docs = await _filter_results(merged_docs)

    total = max(meili_result.get("total") or 0, len(merged_docs))
    start = (page - 1) * size
    paged_docs = merged_docs[start:start + size]

    uploader_map = await _batch_load_uploaders(db, paged_docs)
    items = [_doc_to_item(d, uploader_map.get(d.uploader_id)) for d in paged_docs]
    for it, d in zip(items, paged_docs):
        it.snippet = _snippet(d.content_text, q)

    return SearchResult(items=items, total=total, query=q, page=page, size=size)
