"""LangGraph workflow state definition.

State is a plain, JSON-serializable `TypedDict` (not a domain dataclass)
because LangGraph nodes read/write partial state dicts and the graph
itself has no business knowing about our ORM or dataclasses. The
orchestration service (`app.services.workflow_service`) is the single
boundary that converts between `WorkflowState` and the `AgentRun`
domain aggregate for persistence.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class WorkflowState(TypedDict, total=False):
    run_id: str
    request: str

    plan: list[dict]
    architecture: dict | None
    files: list[dict]
    review: dict | None
    test_report: dict | None
    documentation: str

    status: str
    review_iterations: int
    test_iterations: int
    max_review_iterations: int
    max_test_repair_iterations: int
    error: str | None

    # RAG: relevant chunks retrieved from reference docs + the project's own
    # existing files, surfaced to Planner/Architect for grounded context.
    retrieved_context: list[dict]

    # `operator.add` lets multiple nodes append to the transcript across
    # graph steps without clobbering each other's entries.
    messages: Annotated[list[dict], operator.add]


def initial_state(
    *,
    run_id: str,
    request: str,
    max_review_iterations: int,
    max_test_repair_iterations: int,
    seed_files: list[dict] | None = None,
    seed_architecture: dict | None = None,
    retrieved_context: list[dict] | None = None,
) -> WorkflowState:
    return WorkflowState(
        run_id=run_id,
        request=request,
        plan=[],
        architecture=seed_architecture,
        files=seed_files or [],
        review=None,
        test_report=None,
        documentation="",
        status="pending",
        review_iterations=0,
        test_iterations=0,
        max_review_iterations=max_review_iterations,
        max_test_repair_iterations=max_test_repair_iterations,
        error=None,
        messages=[],
        retrieved_context=retrieved_context or [],
    )
