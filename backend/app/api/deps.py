"""FastAPI dependency providers.

`get_db_session` gives each request its own DB session, scoped to the
request lifetime, committed on success and rolled back on error.
`ProjectService` is built per-request on top of that session.
`WorkflowService` manages its own short-lived sessions internally (it
needs to persist state incrementally across multiple LangGraph steps
inside a single streaming response, so a single request-scoped session
would hold a transaction open for the whole run) and is built from the
process-lifetime `Container`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import Container
from app.db.repository import SqlAlchemyProjectRepository
from app.services.project_service import ProjectService
from app.services.rag_service import RagService
from app.services.workflow_service import WorkflowService


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    container: Container = request.app.state.container
    session = container.session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_project_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectService:
    return ProjectService(SqlAlchemyProjectRepository(session))


async def get_rag_service(container: Container = Depends(get_container)) -> RagService:
    return container.rag_service


async def get_workflow_service(
    container: Container = Depends(get_container),
) -> WorkflowService:
    return WorkflowService(
        container.session_factory,
        container.compiled_graph,
        container.settings,
        rag_service=container.rag_service,
        git_service=container.git_service,
    )
