"""Sandboxed local code execution.

The Tester agent does not ask the LLM whether tests "would" pass -- it
writes the Coder's generated files to an isolated temp workspace and
actually runs `pytest` against them via subprocess, then parses the real
result. This is the one place in the system that touches the filesystem
and spawns processes, so it is deliberately small, defensively coded,
and time-boxed.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_SUMMARY_RE = re.compile(
    r"(?P<passed>\d+) passed"
    r"(?:, (?P<failed_alt>\d+) failed)?"
    r"|(?P<failed>\d+) failed"
)


@dataclass(slots=True)
class ExecutionResult:
    verdict: str  # "passed" | "failed"
    cases: list[dict]
    summary: str
    raw_stdout: str
    raw_stderr: str


class SandboxExecutor:
    """Executes a generated Python project's test suite in an isolated dir."""

    def __init__(self, workspace_root: Path, *, timeout_seconds: float = 60.0) -> None:
        self._workspace_root = workspace_root
        self._timeout = timeout_seconds

    async def run_python_tests(self, run_id: str, files: list[dict]) -> ExecutionResult:
        if not any(f["path"].startswith("tests/") or "test_" in f["path"] for f in files):
            return ExecutionResult(
                verdict="failed",
                cases=[],
                summary="No test files were found among the generated files.",
                raw_stdout="",
                raw_stderr="",
            )

        workdir = (self._workspace_root / f"run-{run_id}-{uuid.uuid4().hex[:8]}").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        try:
            self._materialize_files(workdir, files)
            return await self._execute_pytest(workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _materialize_files(self, workdir: Path, files: list[dict]) -> None:
        for f in files:
            if f.get("change_type") == "delete":
                continue
            target = (workdir / f["path"]).resolve()
            if not str(target).startswith(str(workdir.resolve())):
                # Defend against path traversal from a misbehaving LLM response.
                logger.warning("Skipping file with unsafe path: %s", f["path"])
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.get("content", ""), encoding="utf-8")

        # Ensure package directories are importable even if the model forgot __init__.py.
        for directory in {p.parent for p in workdir.rglob("*.py")}:
            init_file = directory / "__init__.py"
            if not init_file.exists():
                init_file.touch()

        # Critical: pytest discovers its config by walking UPWARD from the target
        # directory until it finds a pytest.ini/pyproject.toml/tox.ini/setup.cfg.
        # If `workdir` happens to live anywhere under this backend's own project
        # tree, pytest would find *our* pytest.ini (with `pythonpath = .`), which
        # puts this backend's real `app` package on sys.path -- silently shadowing
        # the sandboxed project's own `app` package and breaking imports/collection
        # in ways that look like "no tests ran" rather than a clear error. Placing
        # an empty ini file directly in `workdir` makes pytest stop its upward
        # search right here, fully isolating the sandbox's config from ours.
        ini_path = workdir / "pytest.ini"
        if not ini_path.exists():
            ini_path.write_text("[pytest]\n", encoding="utf-8")

    async def _execute_pytest(self, workdir: Path) -> ExecutionResult:
        try:
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            proc = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "pytest",
                "-v",
                "--no-header",
                "-p",
                "no:cacheprovider",
                str(workdir),
                cwd=str(workdir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    verdict="failed",
                    cases=[],
                    summary=f"Test execution timed out after {self._timeout}s.",
                    raw_stdout="",
                    raw_stderr="",
                )
        except FileNotFoundError as exc:
            return ExecutionResult(
                verdict="failed",
                cases=[],
                summary=f"Could not launch test runner: {exc}",
                raw_stdout="",
                raw_stderr="",
            )

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        result = self._parse_pytest_output(stdout, stderr, proc.returncode or 0)
        if result.verdict == "failed":
            logger.info("Sandbox pytest run failed for workdir=%s: %s", workdir, result.summary)
        return result

    def _parse_pytest_output(self, stdout: str, stderr: str, returncode: int) -> ExecutionResult:
        cases: list[dict] = []
        for line in stdout.splitlines():
            match = re.match(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)", line)
            if match:
                cases.append(
                    {
                        "name": match.group(1),
                        "passed": match.group(2) == "PASSED",
                        "output": line.strip(),
                    }
                )

        verdict = "passed" if returncode == 0 else "failed"
        summary_match = _SUMMARY_RE.search(stdout)
        summary = summary_match.group(0) if summary_match else stdout.strip().splitlines()[-1:]
        summary = summary if isinstance(summary, str) else " ".join(summary)

        return ExecutionResult(
            verdict=verdict,
            cases=cases,
            summary=summary or f"pytest exited with code {returncode}",
            raw_stdout=stdout[-4000:],
            raw_stderr=stderr[-2000:],
        )
