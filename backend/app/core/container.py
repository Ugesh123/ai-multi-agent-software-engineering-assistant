"""Application-scoped dependency injection container.

FastAPI's own `Depends` system handles per-request wiring; this container
holds the handful of expensive, process-lifetime singletons (the DB engine,
the LLM provider, the compiled LangGraph workflow) that are built once at
startup and handed to every request via `app.state`. Keeping this in one
object -- rather than scattering `lru_cache`d globals across modules --
makes the object graph explicit and trivially replaceable in tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.config import Settings
from app.db.base import create_engine, create_session_factory
from app.graph.factory import build_compiled_graph
from app.llm.base import LLMProvider
from app.llm.factory import build_llm_provider
from app.rag.base import EmbeddingProvider
from app.rag.factory import build_embedding_provider
from app.services.git_service import GitService
from app.services.rag_service import RagService


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker
    llm_provider: LLMProvider
    embedding_provider: EmbeddingProvider
    compiled_graph: object
    rag_service: RagService
    git_service: GitService

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        llm_provider = build_llm_provider(settings)
        embedding_provider = build_embedding_provider(settings)
        compiled_graph = build_compiled_graph(settings, llm_provider)
        rag_service = RagService(session_factory, embedding_provider)
        git_service = GitService(settings.workspace_root / "repos")

        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,
            compiled_graph=compiled_graph,
            rag_service=rag_service,
            git_service=git_service,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()
