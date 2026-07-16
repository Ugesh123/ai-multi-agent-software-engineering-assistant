"""Framework-agnostic domain entities.

These dataclasses are the core of the application in Clean Architecture
terms: they know nothing about FastAPI, SQLAlchemy, or LangGraph. The
persistence layer (`app.db.models`) and API layer (`app.api.schemas`)
each maintain their own representations and convert to/from these types
at the boundary, so a change in the ORM or the wire format never leaks
into business logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.enums import (
    AgentRole,
    FileChangeType,
    ReviewVerdict,
    RunStatus,
    TestVerdict,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PlanItem:
    """A single actionable task produced by the Planner agent."""

    id: str = field(default_factory=_new_id)
    title: str = ""
    description: str = ""
    order: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArchitectureComponent:
    """A component/module in the system design produced by the Architect."""

    name: str
    responsibility: str
    interfaces: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArchitectureDecision:
    """Full design output of the Architect agent."""

    summary: str = ""
    components: list[ArchitectureComponent] = field(default_factory=list)
    tech_choices: dict[str, str] = field(default_factory=dict)
    file_layout: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GeneratedFile:
    """A single source file produced or modified by the Coder agent."""

    path: str
    content: str
    change_type: FileChangeType = FileChangeType.CREATE
    language: str = "text"

    @property
    def change_type_value(self) -> str:
        """Normalized string value of `change_type`.

        Dataclasses don't coerce/validate field types, and several code
        paths construct `GeneratedFile` from plain dicts sourced from
        LLM/JSON output where `change_type` ends up as a raw string rather
        than a `FileChangeType` enum member. This property is the single
        place that handles both cases, replacing what used to be duplicated
        `getattr(file.change_type, "value", file.change_type)` calls.
        """

        return getattr(self.change_type, "value", self.change_type)


@dataclass(slots=True)
class ReviewFinding:
    """One issue raised by the Reviewer agent against a generated file."""

    file_path: str
    severity: str  # "blocker" | "major" | "minor" | "nit"
    message: str
    line: int | None = None


@dataclass(slots=True)
class ReviewResult:
    verdict: ReviewVerdict = ReviewVerdict.CHANGES_REQUESTED
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""


@dataclass(slots=True)
class TestCaseResult:
    name: str
    passed: bool
    output: str = ""


@dataclass(slots=True)
class TestReport:
    verdict: TestVerdict = TestVerdict.FAILED
    cases: list[TestCaseResult] = field(default_factory=list)
    summary: str = ""


@dataclass(slots=True)
class AgentMessage:
    """A single audit-log entry describing what one agent did during a run."""

    id: str = field(default_factory=_new_id)
    role: AgentRole = AgentRole.PLANNER
    content: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ReferenceDocument:
    """A user-uploaded spec/reference file attached to a project for RAG."""

    id: str = field(default_factory=_new_id)
    project_id: str = ""
    filename: str = ""
    content_type: str = "text/plain"
    extracted_text: str = ""
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(slots=True)
class RetrievedChunk:
    """A single retrieval result returned by the RAG service."""

    source_type: str  # "generated_file" | "reference_doc"
    source_label: str
    content: str
    score: float


@dataclass(slots=True)
class Project:
    """A user-created workspace that groups one or more agent runs."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(slots=True)
class AgentRun:
    """A single end-to-end execution of the multi-agent workflow."""

    id: str = field(default_factory=_new_id)
    project_id: str = ""
    request: str = ""
    status: RunStatus = RunStatus.PENDING
    parent_run_id: str | None = None
    version: int = 1
    commit_message: str = ""
    model: str | None = None
    plan: list[PlanItem] = field(default_factory=list)
    architecture: ArchitectureDecision | None = None
    files: list[GeneratedFile] = field(default_factory=list)
    review: ReviewResult | None = None
    test_report: TestReport | None = None
    documentation: str = ""
    messages: list[AgentMessage] = field(default_factory=list)
    review_iterations: int = 0
    test_iterations: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def record(self, role: AgentRole, content: str, **metadata: str) -> None:
        self.messages.append(AgentMessage(role=role, content=content, metadata=metadata))
        self.updated_at = _utc_now()
