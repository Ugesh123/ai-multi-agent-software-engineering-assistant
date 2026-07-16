from __future__ import annotations

import uuid

import pytest

from app.agents.coder import CoderAgent
from app.agents.state import initial_state
from app.core.exceptions import AgentExecutionError
from app.domain.enums import RunStatus
from app.graph.factory import build_compiled_graph
from app.llm.mock_provider import MockProvider

pytestmark = pytest.mark.asyncio


async def test_coder_merges_partial_output_with_existing_files():
    """The Coder should only need to describe what changed; unrelated
    existing files must survive untouched in the merged result."""

    only_new_file_response = """
{
  "files": [
    {"path": "app/extra.py", "change_type": "create", "language": "python", "content": "def extra():\\n    return 42\\n"}
  ]
}
"""
    agent = CoderAgent(MockProvider({"CODER": only_new_file_response}))
    state = {
        "run_id": "r1",
        "request": "add an extra helper",
        "architecture": {},
        "files": [
            {"path": "app/core.py", "content": "def run(x):\n    return x * 2\n", "change_type": "update", "language": "python"},
            {"path": "tests/test_core.py", "content": "def test_x(): pass", "change_type": "update", "language": "python"},
        ],
    }

    patch = await agent.run(state)

    paths = {f["path"] for f in patch["files"]}
    assert paths == {"app/core.py", "tests/test_core.py", "app/extra.py"}
    core_file = next(f for f in patch["files"] if f["path"] == "app/core.py")
    assert core_file["content"] == "def run(x):\n    return x * 2\n"


async def test_coder_delete_removes_file_from_merged_set():
    delete_response = """
{
  "files": [
    {"path": "app/obsolete.py", "change_type": "delete", "language": "python", "content": ""}
  ]
}
"""
    agent = CoderAgent(MockProvider({"CODER": delete_response}))
    state = {
        "run_id": "r1",
        "request": "remove obsolete module",
        "architecture": {},
        "files": [
            {"path": "app/core.py", "content": "ok", "change_type": "update", "language": "python"},
            {"path": "app/obsolete.py", "content": "stale", "change_type": "update", "language": "python"},
        ],
    }

    patch = await agent.run(state)
    paths = {f["path"] for f in patch["files"]}
    assert paths == {"app/core.py"}


async def test_coder_deleting_all_files_raises():
    delete_all_response = """
{
  "files": [
    {"path": "only.py", "change_type": "delete", "language": "python", "content": ""}
  ]
}
"""
    agent = CoderAgent(MockProvider({"CODER": delete_all_response}))
    state = {
        "run_id": "r1",
        "request": "remove everything",
        "architecture": {},
        "files": [{"path": "only.py", "content": "x", "change_type": "update", "language": "python"}],
    }
    with pytest.raises(AgentExecutionError):
        await agent.run(state)


async def test_edit_mode_workflow_seeds_existing_files_and_merges_new_ones(tmp_path):
    """Full end-to-end: a second run seeded from a first run's completed
    files ends up with BOTH the original files and whatever the (mocked)
    Coder adds on top."""

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.workspace_root = tmp_path

    llm = MockProvider()
    graph = build_compiled_graph(settings, llm)

    first_state = initial_state(
        run_id=str(uuid.uuid4()),
        request="Build a function that doubles a number, with a test.",
        max_review_iterations=settings.max_review_iterations,
        max_test_repair_iterations=settings.max_test_repair_iterations,
    )
    first_result = await graph.ainvoke(first_state)
    assert first_result["status"] == RunStatus.COMPLETED.value
    original_paths = {f["path"] for f in first_result["files"]}
    assert original_paths == {"app/core.py", "tests/test_core.py"}

    add_helper_response = """
{
  "files": [
    {"path": "app/helper.py", "change_type": "create", "language": "python", "content": "def helper():\\n    return 1\\n"}
  ]
}
"""
    edit_llm = MockProvider({"CODER": add_helper_response})
    edit_graph = build_compiled_graph(settings, edit_llm)

    second_state = initial_state(
        run_id=str(uuid.uuid4()),
        request="Add a helper function",
        max_review_iterations=settings.max_review_iterations,
        max_test_repair_iterations=settings.max_test_repair_iterations,
        seed_files=[{**f, "change_type": "update"} for f in first_result["files"]],
        seed_architecture=first_result["architecture"],
    )
    second_result = await edit_graph.ainvoke(second_state)

    final_paths = {f["path"] for f in second_result["files"]}
    assert final_paths == {"app/core.py", "tests/test_core.py", "app/helper.py"}
