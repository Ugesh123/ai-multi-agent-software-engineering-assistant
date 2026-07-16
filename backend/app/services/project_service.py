"""Service layer for `Project` CRUD operations.

Thin by design: at this layer there's no business logic beyond what the
repository already provides, but the service boundary exists so the API
layer never talks to a repository directly, and future business rules
(quotas, ownership checks, etc.) have a natural home.
"""

from __future__ import annotations

from app.db.repository import ProjectRepository
from app.domain.models import Project


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    async def create_project(self, name: str, description: str = "") -> Project:
        return await self._repository.create(Project(name=name, description=description))

    async def get_project(self, project_id: str) -> Project:
        return await self._repository.get(project_id)

    async def list_projects(self) -> list[Project]:
        return await self._repository.list_all()

    async def delete_project(self, project_id: str) -> None:
        await self._repository.delete(project_id)

    async def update_project(
        self, project_id: str, *, name: str | None = None, description: str | None = None
    ) -> Project:
        return await self._repository.update(project_id, name=name, description=description)
