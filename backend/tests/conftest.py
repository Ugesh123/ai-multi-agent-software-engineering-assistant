from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import create_engine, create_session_factory, init_models


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_engine(settings)
    await init_models(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    """For services (RagService, WorkflowService) that open their own
    short-lived sessions per operation rather than taking one session.
    Uses a temp FILE-based SQLite db (not ':memory:') because in-memory
    SQLite resets per new connection, which breaks services that open a
    fresh session per operation."""

    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite+aiosqlite:///{tmp_path / 'rag_test.db'}"
    engine = create_engine(settings)
    await init_models(engine)
    factory = create_session_factory(engine)
    try:
        yield factory
    finally:
        await engine.dispose()
