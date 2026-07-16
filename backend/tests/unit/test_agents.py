from __future__ import annotations

import pytest

from app.agents.architect import ArchitectAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.core.exceptions import AgentExecutionError
from app.llm.mock_provider import MockProvider

pytestmark = pytest.mark.asyncio


async def test_planner_agent_produces_ordered_plan():
    agent = PlannerAgent(MockProvider())
    state = {"run_id": "r1", "request": "Build a calculator"}
    patch = await agent.run(state)

    assert patch["status"] == "designing"
    assert len(patch["plan"]) == 3
    assert patch["plan"][0]["order"] == 0
    assert patch["messages"][0]["role"] == "planner"


async def test_planner_rejects_missing_items_key():
    agent = PlannerAgent(MockProvider({"PLANNER": '{"not_items": []}'}))
    with pytest.raises(AgentExecutionError):
        await agent.run({"run_id": "r1", "request": "x"})


async def test_planner_rejects_empty_plan():
    agent = PlannerAgent(MockProvider({"PLANNER": '{"items": []}'}))
    with pytest.raises(AgentExecutionError):
        await agent.run({"run_id": "r1", "request": "x"})


async def test_architect_agent_produces_design():
    agent = ArchitectAgent(MockProvider())
    state = {"run_id": "r1", "request": "Build a calculator", "plan": []}
    patch = await agent.run(state)

    assert patch["status"] == "coding"
    assert patch["architecture"]["components"]
    assert "file_layout" in patch["architecture"]


async def test_reviewer_approved_sets_status_testing():
    agent = ReviewerAgent(MockProvider())
    state = {"run_id": "r1", "architecture": {}, "files": [], "review_iterations": 0}
    patch = await agent.run(state)

    assert patch["review"]["verdict"] == "approved"
    assert patch["status"] == "testing"
    assert "review_iterations" not in patch


async def test_reviewer_changes_requested_increments_iterations():
    changes_requested_json = (
        '{"verdict": "changes_requested", '
        '"findings": [{"file_path": "a.py", "severity": "major", "message": "bad", "line": null}], '
        '"summary": "needs work"}'
    )
    agent = ReviewerAgent(MockProvider({"REVIEWER": changes_requested_json}))
    state = {"run_id": "r1", "architecture": {}, "files": [], "review_iterations": 0}
    patch = await agent.run(state)

    assert patch["review"]["verdict"] == "changes_requested"
    assert patch["status"] == "coding"
    assert patch["review_iterations"] == 1


async def test_reviewer_rejects_invalid_verdict():
    agent = ReviewerAgent(MockProvider({"REVIEWER": '{"verdict": "maybe", "findings": []}'}))
    with pytest.raises(AgentExecutionError):
        await agent.run({"run_id": "r1", "architecture": {}, "files": [], "review_iterations": 0})


async def test_agent_retries_on_bad_json_then_succeeds():
    """The base agent retries up to max_attempts if JSON parsing fails."""

    call_count = {"n": 0}

    class FlakyProvider(MockProvider):
        async def generate(self, messages, *, temperature=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                from app.llm.base import LLMResponse

                return LLMResponse(content="not json at all", model="mock")
            return await super().generate(messages, temperature=temperature)

    agent = PlannerAgent(FlakyProvider(), max_attempts=2)
    patch = await agent.run({"run_id": "r1", "request": "Build a calculator"})

    assert call_count["n"] == 2
    assert len(patch["plan"]) == 3


async def test_agent_exhausts_retries_and_raises():
    class AlwaysBadProvider(MockProvider):
        async def generate(self, messages, *, temperature=None):
            from app.llm.base import LLMResponse

            return LLMResponse(content="not json", model="mock")

    agent = PlannerAgent(AlwaysBadProvider(), max_attempts=2)
    with pytest.raises(AgentExecutionError):
        await agent.run({"run_id": "r1", "request": "Build a calculator"})
