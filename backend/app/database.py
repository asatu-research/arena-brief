"""Database async engine + session.

Mendukung:
- PostgreSQL via Supabase (transaction pooler port 6543): URL disetel otomatis
  memakai `statement_cache_size=0` (pooler tidak mendukung prepared statements)
  dan SSL.
- Postgres lokal biasa.
"""
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


def _engine_kwargs(url: str) -> dict:
    """Tambah argumen koneksi spesifik asyncpg berdasarkan bentuk URL."""
    host = (urlsplit(url).hostname or "").lower()
    connect_args = {}
    is_supabase = "supabase.com" in host
    if is_supabase:
        # Supabase pooler: butuh SSL + tanpa prepared statements
        connect_args["ssl"] = True
        connect_args["statement_cache_size"] = 0
    return {"connect_args": connect_args}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    **_engine_kwargs(settings.database_url),
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
