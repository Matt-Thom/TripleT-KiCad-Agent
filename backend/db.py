"""Async SQLite persistence layer for TripleT KiCad Agent.

Uses SQLModel on top of SQLAlchemy 2.x async with aiosqlite. The engine and
session factory are module-level singletons, created lazily so tests can point
``TRIPLET_DB_URL`` at a per-test sqlite file and reset the cache.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

DEFAULT_DB_PATH = Path("data") / "triplet.db"
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"

_engine: AsyncEngine | None = None
_session_factory: sessionmaker[AsyncSession] | None = None


def _database_url() -> str:
    return os.getenv("TRIPLET_DB_URL", DEFAULT_DB_URL)


def _ensure_parent_dir(url: str) -> None:
    """Create the parent directory for file-backed sqlite URLs."""
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return
    path_part = url[len(prefix):]
    if not path_part or path_part.startswith(":memory:"):
        return
    parent = Path(path_part).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        url = _database_url()
        _ensure_parent_dir(url)
        _engine = create_async_engine(url, echo=False, future=True)
        _session_factory = sessionmaker(
            bind=_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine


def get_session_factory() -> sessionmaker[AsyncSession]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


async def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    # Import models for their side effect of registering with SQLModel.metadata.
    import backend.models.project  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Async context manager that yields a session and rolls back on error."""
    factory = get_session_factory()
    session: AsyncSession = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """Dispose the engine (useful for tests / shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
