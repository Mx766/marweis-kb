"""Add performance indexes to database tables for ~2000 docs scale."""
import asyncio, sys
sys.path.insert(0, '.')
from app.database import async_session_maker
from sqlalchemy import text

INDEXES = [
    # documents — most frequently queried table
    ("idx_docs_cat_deleted",    "CREATE INDEX IF NOT EXISTS idx_docs_cat_deleted ON documents (category_id, is_deleted)"),
    ("idx_docs_uploader_del",   "CREATE INDEX IF NOT EXISTS idx_docs_uploader_del ON documents (uploader_id, is_deleted)"),
    ("idx_docs_deleted_updated","CREATE INDEX IF NOT EXISTS idx_docs_deleted_updated ON documents (is_deleted, updated_at DESC)"),
    # favorites — high frequency lookups
    ("idx_fav_user_doc",        "CREATE INDEX IF NOT EXISTS idx_fav_user_doc ON favorites (user_id, document_id)"),
    # browse_history — per-user time-ordered queries
    ("idx_history_user_time",   "CREATE INDEX IF NOT EXISTS idx_history_user_time ON browse_history (user_id, created_at DESC)"),
    # categories — tree traversal
    ("idx_cats_parent",         "CREATE INDEX IF NOT EXISTS idx_cats_parent ON categories (parent_id)"),
]

async def main():
    async with async_session_maker() as db:
        for name, sql in INDEXES:
            try:
                await db.execute(text(sql))
                await db.commit()
                print(f"  OK  {name}")
            except Exception as e:
                print(f"  ERR {name}: {e}")
        print("\nDone. Run EXPLAIN ANALYZE on slow queries to verify index usage.")

if __name__ == '__main__':
    asyncio.run(main())
