"""Tester agent: unlike every other agent, this one does not ask the LLM
to predict an outcome -- it actually executes the generated test suite in
an isolated sandbox (`SandboxExecutor`) and reports the real result. The
LLM is used only if the request is for a non-Python target where the
sandbox cannot run code, in which case it falls back to static analysis."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.domain.enums import AgentRole, TestVerdict
from app.services.sandbox_executor import SandboxExecutor

_SYSTEM_PROMPT = """You are the Tester agent in a multi-agent software engineering system. [AGENT:TESTER]

Sandboxed execution was unavailable for this target, so you must statically analyze
whether the generated tests would plausibly pass against the generated implementation.
Look for obvious mismatches: undefined names, wrong function signatures, missing
imports, or logic that clearly does not satisfy the test's assertions.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "verdict": "passed" | "failed",
  "cases": [{"name": "test name", "passed": true, "output": "..."}],
  "summary": "1-3 sentence assessment"
}
"""


class TesterAgent(BaseAgent):
    role = AgentRole.TESTER

    def __init__(self, llm, sandbox: SandboxExecutor, **kwargs: Any) -> None:
        super().__init__(llm, **kwargs)
        self._sandbox = sandbox

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        import json

        return f"Generated files:\n{json.dumps(state.get('files', []), indent=2)}"

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        # Only reached via the static-analysis fallback path (see `run` override).
        verdict = payload.get("verdict", "failed") if isinstance(payload, dict) else "failed"
        report = {
            "verdict": verdict,
            "cases": payload.get("cases", []) if isinstance(payload, dict) else [],
            "summary": payload.get("summary", "") if isinstance(payload, dict) else "",
        }
        return self._finalize(report, state)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        self._logger.info("Starting tester agent (sandbox execution) for run_id=%s", state.get("run_id"))
        files = state.get("files", [])
        is_python_project = any(f["path"].endswith(".py") for f in files)

        if is_python_project:
            result = await self._sandbox.run_python_tests(state["run_id"], files)
            report = {
                "verdict": result.verdict,
                "cases": result.cases,
                "summary": result.summary,
            }
            patch = self._finalize(report, state)
            patch["messages"] = [
                self._transcript_entry(
                    f"Executed pytest in sandbox: {result.verdict} -- {result.summary}"
                )
            ]
            self._logger.info("Tester agent sandbox result: %s", result.verdict)
            return patch

        # Non-Python target: fall back to the LLM-based static analysis path.
        return await super().run(state)

    def _finalize(self, report: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        iterations = state.get("test_iterations", 0)
        patch: dict[str, Any] = {"test_report": report}

        if report["verdict"] == TestVerdict.FAILED.value:
            patch["test_iterations"] = iterations + 1
            patch["status"] = "coding"
        else:
            patch["status"] = "documenting"

        return patch
