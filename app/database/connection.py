from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings

DB_TIMEOUT_SECONDS = 5


@lru_cache
def get_engine() -> AsyncEngine:
    url = get_settings().database_url
    if url.startswith("sqlite"):
        # SQLite is only used by the test suite; no pooling so connections never outlive an event loop.
        return create_async_engine(url, poolclass=NullPool)
    connect_args = {"timeout": DB_TIMEOUT_SECONDS} if url.startswith("postgresql+asyncpg") else {}
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request."""
    async with get_sessionmaker()() as session:
        yield session


async def check_database() -> None:
    """Raises if the database cannot answer a trivial query."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
