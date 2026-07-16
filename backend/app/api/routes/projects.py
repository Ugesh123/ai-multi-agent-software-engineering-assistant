from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_project_service
from app.api.schemas import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await service.create_project(payload.name, payload.description)
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    projects = await service.list_projects()
    return [ProjectResponse.from_domain(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await service.get_project(project_id)
    return ProjectResponse.from_domain(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await service.update_project(
        project_id, name=payload.name, description=payload.description
    )
    return ProjectResponse.from_domain(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> None:
    await service.delete_project(project_id)
