from __future__ import annotations

import os

import pytest

from app.services.sandbox_executor import SandboxExecutor

pytestmark = pytest.mark.asyncio

_PASSING_FILES = [
    {
        "path": "app/core.py",
        "content": "def run(value):\n    return value * 2\n",
        "change_type": "create",
        "language": "python",
    },
    {
        "path": "tests/test_core.py",
        "content": "from app.core import run\n\n\ndef test_run_doubles_value():\n    assert run(3) == 6\n",
        "change_type": "create",
        "language": "python",
    },
]


async def test_sandbox_runs_and_passes_with_absolute_workspace_root(tmp_path):
    executor = SandboxExecutor(tmp_path)
    result = await executor.run_python_tests("run-1", _PASSING_FILES)
    assert result.verdict == "passed"
    assert len(result.cases) == 1
    assert result.cases[0]["passed"] is True


async def test_sandbox_runs_and_passes_with_relative_workspace_root(tmp_path, monkeypatch):
    """Regression test: passing a *relative* workspace_root (as
    `Settings.workspace_root` used to allow) must not break test execution.

    Root cause of the original bug: `workdir` was built from a relative
    `workspace_root` and then used as BOTH the subprocess `cwd` and pytest's
    target path argument. After the subprocess `chdir`s into `workdir`, a
    still-relative target argument gets resolved a second time relative to
    the new cwd, pointing at a path that doesn't exist -- pytest silently
    collects zero tests instead of erroring loudly. `SandboxExecutor` must
    resolve `workdir` to an absolute path internally regardless of what it
    was constructed with.
    """

    monkeypatch.chdir(tmp_path)
    relative_root = os.path.relpath(tmp_path / "workspaces", start=tmp_path)

    executor = SandboxExecutor(tmp_path / "workspaces")
    result = await executor.run_python_tests("run-2", _PASSING_FILES)

    assert result.verdict == "passed", result.raw_stdout + result.raw_stderr
    assert len(result.cases) == 1
    # sanity: confirm we actually exercised a relative-looking root, not an
    # already-absolute one the test happened to construct.
    assert not relative_root.startswith("/")


async def test_sandbox_reports_failure_for_broken_code(tmp_path):
    files = [
        {
            "path": "app/core.py",
            "content": "def run(value):\n    return value * 3\n",  # wrong: triples instead of doubles
            "change_type": "create",
            "language": "python",
        },
        {
            "path": "tests/test_core.py",
            "content": "from app.core import run\n\n\ndef test_run_doubles_value():\n    assert run(3) == 6\n",
            "change_type": "create",
            "language": "python",
        },
    ]
    executor = SandboxExecutor(tmp_path)
    result = await executor.run_python_tests("run-3", files)
    assert result.verdict == "failed"
    assert result.cases[0]["passed"] is False


async def test_sandbox_reports_no_test_files_without_running_pytest(tmp_path):
    files = [
        {"path": "app/core.py", "content": "x = 1\n", "change_type": "create", "language": "python"}
    ]
    executor = SandboxExecutor(tmp_path)
    result = await executor.run_python_tests("run-4", files)
    assert result.verdict == "failed"
    assert "No test files" in result.summary


async def test_sandbox_ignores_deleted_files(tmp_path):
    files = _PASSING_FILES + [
        {"path": "old_module.py", "content": "BROKEN SYNTAX (((", "change_type": "delete", "language": "python"}
    ]
    executor = SandboxExecutor(tmp_path)
    result = await executor.run_python_tests("run-5", files)
    assert result.verdict == "passed"


async def test_sandbox_cleans_up_workdir_after_execution(tmp_path):
    executor = SandboxExecutor(tmp_path)
    await executor.run_python_tests("run-6", _PASSING_FILES)
    remaining = list(tmp_path.glob("run-run-6-*"))
    assert remaining == []
