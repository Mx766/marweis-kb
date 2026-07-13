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


def get_search_client():
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


def index_document(doc: Document):
    """Add or update a document in Meilisearch index."""
    try:
        client = get_search_client()
        client.index("documents").add_documents([{
            "id": str(doc.id),
            "title": doc.title,
            "content": doc.summary or "",
            "tags": doc.tags or [],
            "summary": doc.summary or "",
            "category_id": str(doc.category_id) if doc.category_id else None,
            "file_type": doc.file_type,
            "file_ext": doc.file_ext,
            "uploader_id": str(doc.uploader_id),
            "source": doc.source or "",
            "created_at": doc.created_at.isoformat() if doc.created_at else "",
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
        }])
    except Exception:
        logger.warning("Failed to index document in Meilisearch", exc_info=True)


def remove_document(doc_id: str):
    """Remove a document from Meilisearch index."""
    try:
        client = get_search_client()
        client.index("documents").delete_document(doc_id)
    except Exception:
        logger.warning("Failed to remove document from Meilisearch", exc_info=True)


def search_documents(
    query: str,
    page: int = 1,
    size: int = 20,
    category_id: str | None = None,
    file_type: str | None = None,
    allowed_category_ids: list[str] | None = None,
) -> dict:
    """Search Meilisearch and return results with total count."""
    try:
        client = get_search_client()
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

        result = client.index("documents").search(
            query or "",
            {
                "filter": filter_str,
                "page": page,
                "hitsPerPage": size,
                "attributesToHighlight": ["title", "content", "summary"],
            },
        )
        return {
            "hits": result["hits"],
            "total": result["estimatedTotalHits"],
            "page": page,
            "size": size,
            "query": query,
        }
    except Exception:
        logger.warning("Meilisearch search failed, falling back to SQL", exc_info=True)
        return {"hits": [], "total": 0, "page": page, "size": size, "query": query}
