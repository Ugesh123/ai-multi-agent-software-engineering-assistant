"""Repository pattern for `Project` and `AgentRun` aggregates.

Services depend on the abstract `ProjectRepository` / `AgentRunRepository`
protocols, not on SQLAlchemy directly. This keeps the service layer
testable with in-memory fakes and makes swapping SQLite for Postgres a
zero-change operation for calling code (only `app.core.config.database_url`
changes).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.mappers import project_to_domain, project_to_orm, run_to_domain, run_to_orm
from app.db.models import AgentRunORM, ProjectORM
from app.domain.models import AgentRun, Project


class ProjectRepository(ABC):
    @abstractmethod
    async def create(self, project: Project) -> Project: ...

    @abstractmethod
    async def get(self, project_id: str) -> Project: ...

    @abstractmethod
    async def list_all(self) -> list[Project]: ...

    @abstractmethod
    async def delete(self, project_id: str) -> None: ...

    @abstractmethod
    async def update(self, project_id: str, *, name: str | None, description: str | None) -> Project: ...


class AgentRunRepository(ABC):
    @abstractmethod
    async def create(self, run: AgentRun) -> AgentRun: ...

    @abstractmethod
    async def update(self, run: AgentRun) -> AgentRun: ...

    @abstractmethod
    async def get(self, run_id: str) -> AgentRun: ...

    @abstractmethod
    async def list_for_project(self, project_id: str) -> list[AgentRun]: ...

    @abstractmethod
    async def get_max_version(self, project_id: str) -> int: ...


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project: Project) -> Project:
        row = project_to_orm(project)
        self._session.add(row)
        await self._session.flush()
        return project_to_domain(row)

    async def get(self, project_id: str) -> Project:
        row = await self._session.get(ProjectORM, project_id)
        if row is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project_to_domain(row)

    async def list_all(self) -> list[Project]:
        result = await self._session.execute(
            select(ProjectORM).order_by(ProjectORM.created_at.desc())
        )
        return [project_to_domain(row) for row in result.scalars().all()]

    async def delete(self, project_id: str) -> None:
        row = await self._session.get(ProjectORM, project_id)
        if row is None:
            raise NotFoundError(f"Project {project_id} not found")
        await self._session.delete(row)
        await self._session.flush()

    async def update(
        self, project_id: str, *, name: str | None, description: str | None
    ) -> Project:
        row = await self._session.get(ProjectORM, project_id)
        if row is None:
            raise NotFoundError(f"Project {project_id} not found")
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        await self._session.flush()
        return project_to_domain(row)


class SqlAlchemyAgentRunRepository(AgentRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: AgentRun) -> AgentRun:
        row = run_to_orm(run)
        self._session.add(row)
        await self._session.flush()
        return run_to_domain(row)

    async def update(self, run: AgentRun) -> AgentRun:
        row = await self._session.get(AgentRunORM, run.id)
        if row is None:
            raise NotFoundError(f"AgentRun {run.id} not found")
        new_row = run_to_orm(run)
        for column in AgentRunORM.__table__.columns.keys():
            if column == "id":
                continue
            setattr(row, column, getattr(new_row, column))
        await self._session.flush()
        return run_to_domain(row)

    async def get(self, run_id: str) -> AgentRun:
        row = await self._session.get(AgentRunORM, run_id)
        if row is None:
            raise NotFoundError(f"AgentRun {run_id} not found")
        return run_to_domain(row)

    async def list_for_project(self, project_id: str) -> list[AgentRun]:
        result = await self._session.execute(
            select(AgentRunORM)
            .where(AgentRunORM.project_id == project_id)
            .order_by(AgentRunORM.created_at.desc())
        )
        return [run_to_domain(row) for row in result.scalars().all()]

    async def get_max_version(self, project_id: str) -> int:
        """Lightweight version lookup: a single SQL MAX() aggregate rather
        than loading and deserializing every run (including large nested
        JSON blobs of files/plan/review/etc.) just to find one integer."""

        result = await self._session.execute(
            select(func.max(AgentRunORM.version)).where(AgentRunORM.project_id == project_id)
        )
        return result.scalar() or 0
