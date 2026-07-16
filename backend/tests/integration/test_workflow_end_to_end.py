from __future__ import annotations

import uuid

import pytest

from app.agents.state import initial_state
from app.domain.enums import RunStatus
from app.graph.factory import build_compiled_graph
from app.llm.mock_provider import MockProvider

pytestmark = pytest.mark.asyncio


async def test_full_workflow_runs_planner_through_documentation(tmp_path):
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.workspace_root = tmp_path

    graph = build_compiled_graph(settings, MockProvider())

    state = initial_state(
        run_id=str(uuid.uuid4()),
        request="Build a function that doubles a number, with a test.",
        max_review_iterations=settings.max_review_iterations,
        max_test_repair_iterations=settings.max_test_repair_iterations,
    )

    final_state = await graph.ainvoke(state)
    # Planner ran
    assert len(final_state["plan"]) == 3
    # Architect ran
    assert final_state["architecture"] is not None
    assert final_state["architecture"]["components"]
    # Coder ran and produced real files
    assert len(final_state["files"]) == 2
    assert any(f["path"] == "app/core.py" for f in final_state["files"])
    # Reviewer approved (mock always approves)
    assert final_state["review"]["verdict"] == "approved"
    # Tester actually executed pytest in the sandbox and it passed
    assert final_state["test_report"]["verdict"] == "passed"
    assert final_state["test_report"]["cases"]
    # Documentation ran
    assert "Generated Project" in final_state["documentation"]
    # Final status reached completion
    assert final_state["status"] == RunStatus.COMPLETED.value
    # Every agent recorded a transcript entry
    roles_seen = {m["role"] for m in final_state["messages"]}
    assert roles_seen == {"planner", "architect", "coder", "reviewer", "tester", "documentation"}


async def test_workflow_review_loop_caps_at_max_iterations(tmp_path, monkeypatch):
    """A reviewer that always requests changes should not loop forever."""

    from app.agents.reviewer import ReviewerAgent
    from app.core.config import get_settings
    from app.graph.workflow import build_workflow_graph
    from app.agents.architect import ArchitectAgent
    from app.agents.coder import CoderAgent
    from app.agents.documentation import DocumentationAgent
    from app.agents.planner import PlannerAgent
    from app.agents.tester import TesterAgent
    from app.services.sandbox_executor import SandboxExecutor

    class AlwaysRejectReviewer(ReviewerAgent):
        def parse_response(self, payload, state):
            return {
                "review": {
                    "verdict": "changes_requested",
                    "findings": [{"file_path": "x.py", "severity": "major", "message": "nope", "line": None}],
                    "summary": "always rejecting",
                },
                "review_iterations": state.get("review_iterations", 0) + 1,
                "status": "coding",
            }

    get_settings.cache_clear()
    settings = get_settings()
    settings.workspace_root = tmp_path
    settings.max_review_iterations = 1

    llm = MockProvider()
    graph = build_workflow_graph(
        PlannerAgent(llm),
        ArchitectAgent(llm),
        CoderAgent(llm),
        AlwaysRejectReviewer(llm),
        TesterAgent(llm, SandboxExecutor(tmp_path)),
        DocumentationAgent(llm),
    )

    state = initial_state(
        run_id=str(uuid.uuid4()),
        request="Build a function that doubles a number.",
        max_review_iterations=1,
        max_test_repair_iterations=2,
    )

    final_state = await graph.ainvoke(state)

    # Loop stopped at the cap (1) instead of running forever.
    assert final_state["review_iterations"] == 1
    assert final_state["status"] == RunStatus.COMPLETED.value
    assert final_state["review"]["verdict"] == "changes_requested"
