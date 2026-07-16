"""Orchestrates the lifecycle of an `AgentRun`: creation, streamed
LangGraph execution, and incremental persistence after every agent step.

This is the boundary between the framework-agnostic domain layer and the
LangGraph `WorkflowState` dict format -- it is the only place that
converts between the two.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.state import WorkflowState, initial_state
from app.core.config import Settings
from app.core.exceptions import WorkflowError
from app.core.logging import get_logger
from app.db.base import session_scope
from app.db.repository import SqlAlchemyAgentRunRepository
from app.domain.enums import AgentRole, RunStatus
from app.domain.models import (
    AgentMessage,
    AgentRun,
    ArchitectureDecision,
    GeneratedFile,
    PlanItem,
    ReviewFinding,
    ReviewResult,
    TestCaseResult,
    TestReport,
)
from app.services.diff_service import ProjectDiff, compute_diff, generate_commit_message
from app.services.git_service import GitService
from app.services.rag_service import RagService

logger = get_logger(__name__)


class WorkflowService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        compiled_graph: Any,
        settings: Settings,
        rag_service: RagService | None = None,
        git_service: GitService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._graph = compiled_graph
        self._settings = settings
        self._rag_service = rag_service
        self._git_service = git_service

    async def create_run(
        self,
        project_id: str,
        request: str,
        parent_run_id: str | None = None,
        model: str | None = None,
    ) -> AgentRun:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)

            if parent_run_id is not None:
                parent = await repo.get(parent_run_id)
                if parent.project_id != project_id:
                    raise WorkflowError(
                        f"Run {parent_run_id} does not belong to project {project_id}"
                    )
                if parent.status is not RunStatus.COMPLETED:
                    raise WorkflowError(
                        f"Cannot edit from run {parent_run_id}: it has not completed "
                        f"(status={parent.status.value})"
                    )

            next_version = (await repo.get_max_version(project_id)) + 1

            run = AgentRun(
                project_id=project_id,
                request=request,
                status=RunStatus.PENDING,
                parent_run_id=parent_run_id,
                version=next_version,
                model=model,
            )
            return await repo.create(run)

    async def get_run(self, run_id: str) -> AgentRun:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            return await repo.get(run_id)

    async def list_runs_for_project(self, project_id: str) -> list[AgentRun]:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            return await repo.list_for_project(project_id)

    async def stream_run_execution(self, run_id: str) -> AsyncIterator[dict]:
        """Execute the LangGraph workflow for `run_id`, persisting and
        yielding a JSON-serializable event after every agent step."""

        run = await self.get_run(run_id)
        if run.status is not RunStatus.PENDING:
            raise WorkflowError(
                f"Run {run_id} is not pending (status={run.status.value}); cannot start execution"
            )

        await self._update_status(run_id, RunStatus.PLANNING)

        seed_files: list[dict] = []
        seed_architecture: dict | None = None
        if run.parent_run_id is not None:
            parent = await self.get_run(run.parent_run_id)
            seed_files = [
                {
                    "path": f.path,
                    "content": f.content,
                    "change_type": "update",
                    "language": f.language,
                }
                for f in parent.files
            ]
            if parent.architecture is not None:
                from dataclasses import asdict

                seed_architecture = asdict(parent.architecture)

        retrieved_context: list[dict] = []
        if self._rag_service is not None:
            try:
                chunks = await self._rag_service.retrieve(
                    run.project_id, run.request, top_k=self._settings.rag_top_k
                )
                retrieved_context = [
                    {"source_type": c.source_type, "source_label": c.source_label, "content": c.content}
                    for c in chunks
                ]
            except Exception:  # noqa: BLE001 - RAG is best-effort, never blocks a run
                logger.exception("RAG retrieval failed for run_id=%s; continuing without it", run_id)

        state = initial_state(
            run_id=run.id,
            request=run.request,
            max_review_iterations=self._settings.max_review_iterations,
            max_test_repair_iterations=self._settings.max_test_repair_iterations,
            seed_files=seed_files,
            seed_architecture=seed_architecture,
            retrieved_context=retrieved_context,
        )

        graph = self._graph
        if run.model:
            from app.graph.factory import build_compiled_graph
            from app.llm.factory import build_provider_for_model

            provider = build_provider_for_model(self._settings, run.model)
            graph = build_compiled_graph(self._settings, provider)

        try:
            async for step_state in graph.astream(state, stream_mode="values"):
                await self._persist_state(run_id, step_state)
                yield self._build_event(run_id, step_state)

            await self._finalize_commit_message(run_id, run.parent_run_id)
            await self._sync_rag_and_git(run_id, run.project_id)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client and persisted
            logger.exception("Workflow execution failed for run_id=%s", run_id)
            await self._mark_failed(run_id, str(exc))
            yield {"run_id": run_id, "status": RunStatus.FAILED.value, "error": str(exc)}
            raise

    async def _sync_rag_and_git(self, run_id: str, project_id: str) -> None:
        """Re-index generated files for RAG and mirror this version into
        the project's git repo. Best-effort: neither failure aborts the run,
        since the run itself already succeeded and is fully persisted."""

        run = await self.get_run(run_id)
        if run.status is not RunStatus.COMPLETED:
            return

        if self._rag_service is not None:
            try:
                await self._rag_service.ingest_generated_files(project_id, run.files)
            except Exception:  # noqa: BLE001
                logger.exception("RAG re-indexing failed for run_id=%s", run_id)

        if self._git_service is not None:
            try:
                commit_hash = await self._git_service.commit_version(
                    project_id, run.files, run.commit_message or f"v{run.version}"
                )
                logger.info("Committed v%s for project=%s as %s", run.version, project_id, commit_hash)
            except Exception:  # noqa: BLE001
                logger.exception("Git commit failed for run_id=%s", run_id)

    async def _finalize_commit_message(self, run_id: str, parent_run_id: str | None) -> None:
        """Deterministically compute and persist a commit message summarizing
        this run's changes relative to its parent (or from-scratch baseline)."""

        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            run = await repo.get(run_id)
            if run.status is not RunStatus.COMPLETED:
                return

            baseline_files = []
            if parent_run_id is not None:
                parent = await repo.get(parent_run_id)
                baseline_files = parent.files

            diff = compute_diff(baseline_files, run.files)
            run.commit_message = generate_commit_message(run.request, diff)
            await repo.update(run)

    async def get_diff(self, run_id: str, compare_to: str | None = None) -> ProjectDiff:
        """Diff `run_id` against `compare_to` (or its parent, or an empty
        baseline if it has none)."""

        run = await self.get_run(run_id)
        baseline_id = compare_to if compare_to is not None else run.parent_run_id

        baseline_files = []
        if baseline_id is not None:
            baseline_run = await self.get_run(baseline_id)
            if baseline_run.project_id != run.project_id:
                raise WorkflowError(
                    f"Cannot compare run {run_id} against run {baseline_id}: "
                    "they belong to different projects"
                )
            baseline_files = baseline_run.files

        return compute_diff(baseline_files, run.files)

    async def restore_version(self, project_id: str, source_run_id: str) -> AgentRun:
        """Create a new run whose files/architecture/documentation are an
        exact copy of `source_run_id`'s -- no agents involved, since this is
        a pure, instantaneous rollback rather than a regeneration."""

        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)

            source = await repo.get(source_run_id)
            if source.project_id != project_id:
                raise WorkflowError(
                    f"Run {source_run_id} does not belong to project {project_id}"
                )
            if source.status is not RunStatus.COMPLETED:
                raise WorkflowError(
                    f"Cannot restore run {source_run_id}: it has not completed "
                    f"(status={source.status.value})"
                )

            next_version = (await repo.get_max_version(project_id)) + 1

            restored = AgentRun(
                project_id=project_id,
                request=f"Restore to v{source.version}",
                status=RunStatus.COMPLETED,
                parent_run_id=source_run_id,
                version=next_version,
                plan=source.plan,
                architecture=source.architecture,
                files=source.files,
                review=source.review,
                test_report=source.test_report,
                documentation=source.documentation,
                commit_message=f"Restored to v{source.version}",
            )
            created = await repo.create(restored)

        await self._sync_rag_and_git(created.id, project_id)
        return created

    async def _persist_state(self, run_id: str, state: WorkflowState) -> None:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            run = await repo.get(run_id)
            _apply_state_to_run(run, state)
            await repo.update(run)

    async def _update_status(self, run_id: str, status: RunStatus) -> None:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            run = await repo.get(run_id)
            run.status = status
            await repo.update(run)

    async def _mark_failed(self, run_id: str, error: str) -> None:
        async with session_scope(self._session_factory) as session:
            repo = SqlAlchemyAgentRunRepository(session)
            run = await repo.get(run_id)
            run.status = RunStatus.FAILED
            run.error = error
            await repo.update(run)

    @staticmethod
    def _build_event(run_id: str, state: WorkflowState) -> dict:
        latest_message = state["messages"][-1] if state.get("messages") else None
        return {
            "run_id": run_id,
            "status": state.get("status", "pending"),
            "latest_message": latest_message,
            "review_iterations": state.get("review_iterations", 0),
            "test_iterations": state.get("test_iterations", 0),
        }


def _apply_state_to_run(run: AgentRun, state: WorkflowState) -> None:
    """Mutate `run` in place from a raw LangGraph state dict."""

    if "status" in state:
        # The graph may report "completed" only via the final documentation
        # step; every intermediate step still carries a valid RunStatus value.
        run.status = RunStatus(state["status"])

    if "plan" in state:
        run.plan = [PlanItem(**item) for item in state["plan"]]

    if state.get("architecture") is not None:
        run.architecture = ArchitectureDecision(**state["architecture"])

    if "files" in state:
        run.files = [GeneratedFile(**f) for f in state["files"]]

    if state.get("review") is not None:
        from app.domain.enums import ReviewVerdict

        review = state["review"]
        run.review = ReviewResult(
            verdict=ReviewVerdict(review["verdict"]),
            findings=[ReviewFinding(**f) for f in review.get("findings", [])],
            summary=review.get("summary", ""),
        )

    if state.get("test_report") is not None:
        from app.domain.enums import TestVerdict

        report = state["test_report"]
        run.test_report = TestReport(
            verdict=TestVerdict(report["verdict"]),
            cases=[TestCaseResult(**c) for c in report.get("cases", [])],
            summary=report.get("summary", ""),
        )

    if "documentation" in state and state["documentation"]:
        run.documentation = state["documentation"]

    if "review_iterations" in state:
        run.review_iterations = state["review_iterations"]

    if "test_iterations" in state:
        run.test_iterations = state["test_iterations"]

    if state.get("messages"):
        run.messages = [
            AgentMessage(
                id=m["id"],
                role=AgentRole(m["role"]),
                content=m["content"],
                created_at=datetime.fromisoformat(m["created_at"]),
                metadata=m.get("metadata", {}),
            )
            for m in state["messages"]
        ]
