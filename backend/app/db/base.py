"""Async SQLAlchemy engine and session factory.

Single source of truth for database connectivity. Both the FastAPI
dependency (`app.api.deps.get_db_session`) and test fixtures build on
top of `session_factory` defined here so there is exactly one place
that knows how to talk to the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    connect_args = (
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    )
    return create_async_engine(
        settings.database_url,
        echo=settings.sql_echo,
        connect_args=connect_args,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def init_models(engine: AsyncEngine) -> None:
    """Create all tables. Used at startup and in tests (SQLite-friendly)."""

    # Import models so they're registered on Base.metadata before create_all.
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope: commits on success, rolls back on error."""

    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
