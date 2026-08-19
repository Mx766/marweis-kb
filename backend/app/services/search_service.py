import asyncio
import logging
import threading
import meilisearch
from app.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)

_client: meilisearch.Client | None = None
_lock = threading.Lock()


def _escape_meili_filter_value(value: str) -> str:
    """Escape single quotes in Meilisearch filter values to prevent injection."""
    return value.replace("'", "\\'")


def _get_search_client_sync():
    """Get or create the Meilisearch client (sync, thread-safe)."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
                try:
                    _client.create_index("documents", {"primaryKey": "id"})
                except Exception:
                    pass  # Index already exists
                try:
                    _client.index("documents").update_searchable_attributes([
                        "title", "content", "tags", "summary"
                    ])
                    _client.index("documents").update_filterable_attributes([
                        "category_id", "file_type", "uploader_id"
                    ])
                    _client.index("documents").update_sortable_attributes([
                        "created_at", "updated_at", "title"
                    ])
                except Exception:
                    logger.warning("Failed to configure Meilisearch index settings", exc_info=True)
    return _client


async def index_document(doc: Document):
    """Add or update a document in Meilisearch index (async-safe)."""
    try:
        client = _get_search_client_sync()
        await asyncio.to_thread(
            client.index("documents").add_documents,
            [{
                "id": str(doc.id),
                "title": doc.title,
                "content": (doc.content_text or doc.summary or ""),
                "tags": doc.tags or [],
                "summary": doc.summary or "",
                "category_id": str(doc.category_id) if doc.category_id else None,
                "file_type": doc.file_type,
                "file_ext": doc.file_ext,
                "uploader_id": str(doc.uploader_id),
                "source": doc.source or "",
                "created_at": doc.created_at.isoformat() if doc.created_at else "",
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
            }],
        )
    except Exception:
        logger.warning("Failed to index document in Meilisearch", exc_info=True)
    await index_ai_document(doc)


def _ensure_ai_index(client) -> None:
    try:
        client.create_index("ai_documents", {"primaryKey": "id"})
    except Exception:
        pass
    try:
        client.index("ai_documents").update_searchable_attributes(
            ["title", "markdown_content", "summary"]
        )
        client.index("ai_documents").update_filterable_attributes(["category_id"])
        client.index("ai_documents").update_sortable_attributes(["updated_at"])
    except Exception:
        logger.warning("Failed to configure ai_documents index", exc_info=True)


async def index_ai_document(doc: Document):
    """Add/update a document in the AI-only Meilisearch index."""
    try:
        client = _get_search_client_sync()
        _ensure_ai_index(client)
        await asyncio.to_thread(
            client.index("ai_documents").add_documents,
            [{
                "id": str(doc.id),
                "title": doc.title,
                "markdown_content": doc.markdown_content or "",
                "summary": doc.summary or "",
                "category_id": str(doc.category_id) if doc.category_id else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
            }],
        )
    except Exception:
        logger.warning("Failed to index AI document in Meilisearch", exc_info=True)


async def ai_search_documents(
    query: str,
    size: int = 10,
    allowed_category_ids: list[str] | None = None,
) -> list[dict]:
    """Search the AI-only index; returns hits with markdown snippet."""
    try:
        client = _get_search_client_sync()
        _ensure_ai_index(client)

        def _do():
            filter_parts = []
            if allowed_category_ids:
                cat_filter = " OR ".join(
                    [f"category_id = '{_escape_meili_filter_value(cid)}'" for cid in allowed_category_ids]
                )
                filter_parts.append(f"({cat_filter})")
            filter_str = " AND ".join(filter_parts) if filter_parts else None
            return client.index("ai_documents").search(
                query,
                {
                    "limit": size,
                    "filter": filter_str,
                    "attributesToHighlight": ["title", "markdown_content"],
                    "highlightPreTag": "[[",
                    "highlightPostTag": "]]",
                },
            )

        result = await asyncio.to_thread(_do)
        return result.get("hits", [])
    except Exception:
        logger.warning("Meilisearch AI search failed", exc_info=True)
        return []


async def sync_all_documents(docs: list[Document]) -> int:
    """Batch-index all documents into MeiliSearch. Returns count of indexed docs."""
    try:
        client = _get_search_client_sync()
        idx = client.index("documents")
        # Clear and rebuild
        await asyncio.to_thread(idx.delete_all_documents)
        batch = []
        total = 0
        for doc in docs:
            batch.append({
                "id": str(doc.id),
                "title": doc.title,
                "content": (doc.content_text or doc.summary or ""),
                "tags": doc.tags or [],
                "summary": doc.summary or "",
                "category_id": str(doc.category_id) if doc.category_id else None,
                "file_type": doc.file_type,
                "file_ext": doc.file_ext,
                "uploader_id": str(doc.uploader_id),
                "source": doc.source or "",
                "created_at": doc.created_at.isoformat() if doc.created_at else "",
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
            })
            if len(batch) >= 100:
                await asyncio.to_thread(idx.add_documents, batch)
                total += len(batch)
                batch = []
        if batch:
            await asyncio.to_thread(idx.add_documents, batch)
            total += len(batch)
        logger.info(f"MeiliSearch sync complete: {total} documents indexed")
        return total
    except Exception:
        logger.warning("MeiliSearch sync failed", exc_info=True)
        return 0


async def remove_document(doc_id: str):
    """Remove a document from Meilisearch index (async-safe)."""
    try:
        client = _get_search_client_sync()
        await asyncio.to_thread(
            client.index("documents").delete_document,
            doc_id,
        )
        await asyncio.to_thread(
            client.index("ai_documents").delete_document,
            doc_id,
        )
    except Exception:
        logger.warning("Failed to remove document from Meilisearch", exc_info=True)


async def search_documents(
    query: str,
    page: int = 1,
    size: int = 20,
    category_id: str | None = None,
    file_type: str | None = None,
    allowed_category_ids: list[str] | None = None,
) -> dict:
    """Search Meilisearch and return results with total count (async-safe)."""
    try:
        client = _get_search_client_sync()

        def _do_search():
            filter_parts = []
            if category_id:
                filter_parts.append(f"category_id = '{_escape_meili_filter_value(category_id)}'")
            if file_type:
                filter_parts.append(f"file_type = '{_escape_meili_filter_value(file_type)}'")
            if allowed_category_ids:
                cat_filter = " OR ".join(
                    [f"category_id = '{_escape_meili_filter_value(cid)}'" for cid in allowed_category_ids]
                )
                filter_parts.append(f"({cat_filter})")

            filter_str = " AND ".join(filter_parts) if filter_parts else None

            return client.index("documents").search(
                query or "",
                {
                    "filter": filter_str,
                    "page": page,
                    "hitsPerPage": size,
                    "attributesToHighlight": ["title", "content", "summary"],
                },
            )

        result = await asyncio.to_thread(_do_search)
        return {
            "hits": result["hits"],
            "total": result.get(
                "totalHits",
                result.get("estimatedTotalHits", len(result.get("hits", []))),
            ),
            "page": page,
            "size": size,
            "query": query,
        }
    except Exception:
        logger.warning("Meilisearch search failed, falling back to SQL", exc_info=True)
        return {"hits": [], "total": 0, "page": page, "size": size, "query": query}
