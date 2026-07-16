from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest_asyncio.fixture
async def api_client(tmp_path) -> AsyncIterator[AsyncClient]:
    """A fully wired FastAPI app (real routes, real DB, real LangGraph
    workflow) running against an isolated temp SQLite file and the
    deterministic MockProvider -- no network, no Ollama required."""

    import os

    db_path = tmp_path / f"test-{uuid.uuid4().hex}.db"
    os.environ["MACA_LLM_PROVIDER"] = "mock"
    os.environ["MACA_EMBEDDING_PROVIDER"] = "mock"
    os.environ["MACA_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["MACA_ENVIRONMENT"] = "test"

    get_settings.cache_clear()
    settings = get_settings()
    settings.workspace_root = tmp_path / "workspaces"
    settings.workspace_root.mkdir(parents=True, exist_ok=True)

    from app.main import create_app

    app = create_app()

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    os.environ.pop("MACA_LLM_PROVIDER", None)
    os.environ.pop("MACA_EMBEDDING_PROVIDER", None)
    os.environ.pop("MACA_DATABASE_URL", None)
    os.environ.pop("MACA_ENVIRONMENT", None)
    get_settings.cache_clear()
