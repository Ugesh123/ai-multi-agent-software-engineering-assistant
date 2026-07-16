"""LangGraph state machine wiring all six agents together.

Flow:
    planner -> architect -> coder -> reviewer
        -> [changes_requested & under limit] -> back to coder
        -> [approved | limit reached]         -> tester
    tester
        -> [failed & under limit] -> back to coder
        -> [passed | limit reached] -> documentation -> END

Both feedback loops are iteration-capped by `max_review_iterations` /
`max_test_repair_iterations` (from `Settings`) so a stubborn model can
never spin the graph forever -- after the cap, the workflow proceeds
with the best result obtained so far and the run is still marked
complete, with the outstanding issues visible in `review`/`test_report`.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.architect import ArchitectAgent
from app.agents.coder import CoderAgent
from app.agents.documentation import DocumentationAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.state import WorkflowState
from app.agents.tester import TesterAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


def _route_after_review(state: WorkflowState) -> str:
    review = state.get("review") or {}
    iterations = state.get("review_iterations", 0)
    limit = state.get("max_review_iterations", 2)

    if review.get("verdict") == "changes_requested" and iterations < limit:
        return "coder"
    return "tester"


def _route_after_test(state: WorkflowState) -> str:
    report = state.get("test_report") or {}
    iterations = state.get("test_iterations", 0)
    limit = state.get("max_test_repair_iterations", 2)

    if report.get("verdict") == "failed" and iterations < limit:
        return "coder"
    return "documentation"


def build_workflow_graph(
    planner: PlannerAgent,
    architect: ArchitectAgent,
    coder: CoderAgent,
    reviewer: ReviewerAgent,
    tester: TesterAgent,
    documentation: DocumentationAgent,
):
    """Compile the LangGraph state machine from the six agent instances."""

    graph = StateGraph(WorkflowState)

    graph.add_node("planner", planner.run)
    graph.add_node("architect", architect.run)
    graph.add_node("coder", coder.run)
    graph.add_node("reviewer", reviewer.run)
    graph.add_node("tester", tester.run)
    graph.add_node("documentation", documentation.run)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "reviewer")

    graph.add_conditional_edges(
        "reviewer", _route_after_review, {"coder": "coder", "tester": "tester"}
    )
    graph.add_conditional_edges(
        "tester",
        _route_after_test,
        {"coder": "coder", "documentation": "documentation"},
    )

    graph.add_edge("documentation", END)

    return graph.compile()
