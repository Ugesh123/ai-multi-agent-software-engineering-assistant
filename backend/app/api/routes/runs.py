from __future__ import annotations

import json

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response, StreamingResponse

from app.api.deps import get_project_service, get_workflow_service
from app.api.schemas import (
    ProjectDiffResponse,
    RestoreRequest,
    RunCreateRequest,
    RunResponse,
)
from app.core.exceptions import WorkflowError
from app.domain.enums import RunStatus
from app.services.project_export_service import build_project_zip
from app.services.project_service import ProjectService
from app.services.workflow_service import WorkflowService

router = APIRouter(tags=["runs"])


@router.post(
    "/projects/{project_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    project_id: str,
    payload: RunCreateRequest,
    project_service: ProjectService = Depends(get_project_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> RunResponse:
    # Raises NotFoundError (-> 404) if the project doesn't exist.
    await project_service.get_project(project_id)
    run = await workflow_service.create_run(
        project_id, payload.request, payload.parent_run_id, payload.model
    )
    return RunResponse.from_domain(run)


@router.get("/projects/{project_id}/runs", response_model=list[RunResponse])
async def list_project_runs(
    project_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> list[RunResponse]:
    runs = await workflow_service.list_runs_for_project(project_id)
    return [RunResponse.from_domain(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> RunResponse:
    run = await workflow_service.get_run(run_id)
    return RunResponse.from_domain(run)


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> StreamingResponse:
    """Server-Sent Events stream of workflow progress.

    Executes the (pending) run's LangGraph workflow, persisting to the
    database after every agent step and pushing that same update to the
    client as an SSE `data:` frame. Reconnect-safe: `GET /runs/{id}`
    always reflects the latest persisted state even if the stream itself
    is interrupted mid-run.
    """

    # Validated eagerly, before the StreamingResponse is constructed: SSE
    # responses send their 200 status as soon as streaming begins, so any
    # error raised from *inside* the generator can no longer be mapped to
    # a proper HTTP status code. Checking here lets a bad request (e.g. a
    # run that already completed) surface as a normal 409 JSON error.
    run = await workflow_service.get_run(run_id)
    if run.status is not RunStatus.PENDING:
        raise WorkflowError(
            f"Run {run_id} is not pending (status={run.status.value}); cannot start execution"
        )

    async def event_source():
        async for event in workflow_service.stream_run_execution(run_id):
            yield f"data: {json.dumps(event)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.get("/runs/{run_id}/download")
async def download_run_zip(
    run_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> Response:
    """Download the run's generated files (plus README) as a ZIP archive."""

    run = await workflow_service.get_run(run_id)
    if not run.files:
        raise WorkflowError(f"Run {run_id} has no generated files to download yet")

    archive_bytes = build_project_zip(run)
    filename = f"project-{run_id[:8]}.zip"
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/runs/{run_id}/diff", response_model=ProjectDiffResponse)
async def get_run_diff(
    run_id: str,
    compare_to: str | None = None,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ProjectDiffResponse:
    """Diff this run's files against `compare_to` (another run id), or
    against its parent run if `compare_to` is omitted."""

    diff = await workflow_service.get_diff(run_id, compare_to)
    return ProjectDiffResponse.from_domain(diff)


@router.post(
    "/projects/{project_id}/runs/restore",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def restore_version(
    project_id: str,
    payload: RestoreRequest,
    project_service: ProjectService = Depends(get_project_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> RunResponse:
    """Instantly restore a prior version's files as a new version -- no
    agents are invoked; this is a pure copy, recorded as a new run so
    restoring is itself non-destructive and shows up in version history."""

    await project_service.get_project(project_id)
    restored = await workflow_service.restore_version(project_id, payload.source_run_id)
    return RunResponse.from_domain(restored)
