"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Requires Ollama running locally (`ollama serve`) with the configured
model pulled (default: `qwen3:14b` via `MACA_OLLAMA_MODEL`) unless
`MACA_LLM_PROVIDER=mock` is set for offline development/testing.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes import documents, git, health, models, projects, runs
from app.core.config import get_settings
from app.core.container import Container
from app.core.logging import configure_logging, get_logger
from app.db.base import init_models

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    logger.info(
        "Starting %s (env=%s, llm_provider=%s)",
        settings.app_name,
        settings.environment.value,
        settings.llm_provider.value,
    )

    container = Container.build(settings)
    await init_models(container.engine)
    app.state.container = container

    logger.info("Startup complete")
    yield

    logger.info("Shutting down")
    await container.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(projects.router, prefix=settings.api_v1_prefix)
    app.include_router(runs.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.search_router, prefix=settings.api_v1_prefix)
    app.include_router(models.router, prefix=settings.api_v1_prefix)
    app.include_router(git.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
