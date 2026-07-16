"""API-layer DTOs.

These Pydantic models define the wire format and are deliberately kept
separate from `app.domain.models` (plain dataclasses) so a change to the
public API contract never forces a change to internal business objects,
and vice versa.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import RunStatus
from app.domain.models import AgentRun, Project


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class RunCreateRequest(BaseModel):
    request: str = Field(min_length=1, description="Natural-language feature request")
    parent_run_id: str | None = Field(
        default=None,
        description="If set, the Coder agent edits this prior (completed) run's "
        "files incrementally instead of generating a project from scratch.",
    )
    model: str | None = Field(
        default=None,
        description="Optional per-run model override, e.g. 'llama3' (same provider "
        "type as configured) or 'anthropic:claude-sonnet-4-5' (switch provider).",
    )


class PlanItemResponse(BaseModel):
    id: str
    title: str
    description: str
    order: int
    depends_on: list[str]


class GeneratedFileResponse(BaseModel):
    path: str
    content: str
    change_type: str
    language: str


class RunResponse(BaseModel):
    id: str
    project_id: str
    request: str
    status: RunStatus
    parent_run_id: str | None
    version: int
    commit_message: str
    model: str | None
    plan: list[dict]
    architecture: dict | None
    files: list[dict]
    review: dict | None
    test_report: dict | None
    documentation: str
    review_iterations: int
    test_iterations: int
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, run: AgentRun) -> "RunResponse":
        from dataclasses import asdict

        return cls(
            id=run.id,
            project_id=run.project_id,
            request=run.request,
            status=run.status,
            parent_run_id=run.parent_run_id,
            version=run.version,
            commit_message=run.commit_message,
            model=run.model,
            plan=[asdict(p) for p in run.plan],
            architecture=asdict(run.architecture) if run.architecture else None,
            files=[asdict(f) for f in run.files],
            review=_review_dict(run.review),
            test_report=_test_report_dict(run.test_report),
            documentation=run.documentation,
            review_iterations=run.review_iterations,
            test_iterations=run.test_iterations,
            error=run.error,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )


def _review_dict(review) -> dict | None:
    if review is None:
        return None
    from dataclasses import asdict

    d = asdict(review)
    d["verdict"] = review.verdict.value
    return d


def _test_report_dict(report) -> dict | None:
    if report is None:
        return None
    from dataclasses import asdict

    d = asdict(report)
    d["verdict"] = report.verdict.value
    return d


class ModifiedFileDiffResponse(BaseModel):
    path: str
    unified_diff: str
    added_lines: int
    removed_lines: int


class ProjectDiffResponse(BaseModel):
    added: list[str]
    deleted: list[str]
    modified: list[ModifiedFileDiffResponse]
    unchanged: list[str]

    @classmethod
    def from_domain(cls, diff) -> "ProjectDiffResponse":
        return cls(
            added=diff.added,
            deleted=diff.deleted,
            modified=[
                ModifiedFileDiffResponse(
                    path=m.path,
                    unified_diff=m.unified_diff,
                    added_lines=m.added_lines,
                    removed_lines=m.removed_lines,
                )
                for m in diff.modified
            ],
            unchanged=diff.unchanged,
        )


class RestoreRequest(BaseModel):
    source_run_id: str = Field(description="The run/version to restore")


class ReferenceDocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    content_type: str
    created_at: datetime
    preview: str

    @classmethod
    def from_domain(cls, doc) -> "ReferenceDocumentResponse":
        preview = doc.extracted_text[:300]
        return cls(
            id=doc.id,
            project_id=doc.project_id,
            filename=doc.filename,
            content_type=doc.content_type,
            created_at=doc.created_at,
            preview=preview,
        )


class RetrievedChunkResponse(BaseModel):
    source_type: str
    source_label: str
    content: str
    score: float


class ModelInfo(BaseModel):
    name: str
    provider: str


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    current_default: str


class GitCommitResponse(BaseModel):
    hash: str
    author: str
    date: str
    message: str


class GitRemoteRequest(BaseModel):
    remote_url: str = Field(min_length=1)


class GitPushRequest(BaseModel):
    remote_url: str = Field(min_length=1)
    token: str | None = Field(default=None, description="Never persisted; used only for this push")
    branch: str = "main"


class GitPushResponse(BaseModel):
    success: bool
    output: str


class ErrorResponse(BaseModel):
    error: str
    details: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_healthy: bool
