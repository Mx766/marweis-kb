from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Model(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Yield a database session without auto-commit.

    Callers are responsible for committing or rolling back the session.
    This prevents partial flushes from being automatically committed.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Do NOT auto-commit — let the caller decide the transaction boundary.
            # If the session is dirty and uncommitted, roll back to avoid leaking changes.
            if session.is_active and session.dirty:
                await session.rollback()
