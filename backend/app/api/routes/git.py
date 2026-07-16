from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_container, get_project_service
from app.api.schemas import GitCommitResponse, GitPushRequest, GitPushResponse, GitRemoteRequest
from app.core.container import Container
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects/{project_id}/git", tags=["git"])


@router.get("/log", response_model=list[GitCommitResponse])
async def get_git_log(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    container: Container = Depends(get_container),
) -> list[GitCommitResponse]:
    """Real git log for this project's local repo -- one commit per
    completed version, mirroring the version history exactly."""

    await project_service.get_project(project_id)
    commits = await container.git_service.get_log(project_id)
    return [GitCommitResponse(**c) for c in commits]


@router.post("/remote", status_code=status.HTTP_204_NO_CONTENT)
async def set_git_remote(
    project_id: str,
    payload: GitRemoteRequest,
    project_service: ProjectService = Depends(get_project_service),
    container: Container = Depends(get_container),
) -> None:
    await project_service.get_project(project_id)
    await container.git_service.set_remote(project_id, payload.remote_url)


@router.post("/push", response_model=GitPushResponse)
async def push_to_remote(
    project_id: str,
    payload: GitPushRequest,
    project_service: ProjectService = Depends(get_project_service),
    container: Container = Depends(get_container),
) -> GitPushResponse:
    """Push the project's local git history to a remote. `token` (if any)
    is used only for this single push and is never persisted or logged."""

    await project_service.get_project(project_id)
    result = await container.git_service.push(
        project_id, payload.remote_url, payload.token, payload.branch
    )
    return GitPushResponse(**result)
