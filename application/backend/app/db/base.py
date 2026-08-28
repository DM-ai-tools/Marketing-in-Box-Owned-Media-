"""SQLAlchemy 2.0 declarative base, async engine, and session factory.

The rest of `app/` follows an async-everywhere rule (see backend README's "Architecture note"),
so this module exposes an async engine/session using SQLAlchemy 2.0's asyncio extension with the
`postgresql+psycopg` (psycopg 3) driver, which supports both sync and async connections from the
same DSN — no separate `asyncpg` dependency needed.

`DATABASE_URL` is read lazily (on first use), not at import time. This matters because:
- `app/db/models.py` and this module get imported by Alembic's `env.py` purely to read
  `Base.metadata` for autogenerate/migration purposes. That must work even if `DATABASE_URL`
  is not set in the current shell (Alembic gets its own connection URL independently).
- Importing this module in tests/tools that only need `Base` (e.g. metadata introspection)
  should not require a real database to be reachable.

Usage (FastAPI dependency):
    from app.db.base import get_session

    @router.get(...)
    async def handler(session: AsyncSession = Depends(get_session)) -> ...:
        ...
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in `app/db/models.py`.

    Alembic's `env.py` imports `Base.metadata` as `target_metadata` for autogeneration, so every
    model must attach to this exact `Base` (not a second, accidental `declarative_base()` call
    somewhere else) or it will be invisible to migrations.
    """


def database_url() -> str:
    """Read `DATABASE_URL` from the environment.

    Raises a clear error at the point of use (engine creation) rather than at import time, so
    that importing this module for its metadata/types never requires a database to exist.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy application/backend/.env.example to .env and set a "
            "real Postgres DSN, e.g. postgresql+psycopg://user:password@localhost:5432/marketing_in_a_box"
        )
    return normalize_dsn(url)


def normalize_dsn(url: str) -> str:
    """Force the psycopg 3 driver onto a DSN that does not name one.

    Managed hosts (Railway, Heroku, Render) inject a bare `postgresql://` — or the legacy
    `postgres://` — which SQLAlchemy resolves to psycopg2: a driver this app does not install and,
    being sync-only, one that `create_async_engine` refuses outright. The failure surfaces at the
    first query as a 500, nowhere near the environment variable that caused it, so the scheme is
    corrected here instead of relying on every deployment to spell the DSN exactly right.
    """
    for bare, driver in (("postgresql://", "postgresql+psycopg://"), ("postgres://", "postgresql+psycopg://")):
        if url.startswith(bare):
            return driver + url[len(bare):]
    return url


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use (lazy singleton)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(database_url(), pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a request-scoped `AsyncSession`, closed on request end."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
