"""Reviewer agent: performs a code review of the Coder's output against the
system design, flagging blocking issues that must be fixed before testing."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.domain.enums import AgentRole, ReviewVerdict

_SYSTEM_PROMPT = """You are the Reviewer agent in a multi-agent software engineering system. [AGENT:REVIEWER]

You receive the generated source files and the system design they should satisfy.
Review the code as a senior engineer would: correctness, edge cases, security,
readability, adherence to the design, and missing test coverage. Only request
changes for real, specific problems -- do not nitpick style choices that don't
affect correctness or maintainability. If the code is genuinely production-ready,
approve it.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "verdict": "approved" | "changes_requested",
  "findings": [
    {"file_path": "relative/path.py", "severity": "blocker" | "major" | "minor" | "nit", "message": "...", "line": null}
  ],
  "summary": "1-3 sentence overall assessment"
}
"""


class ReviewerAgent(BaseAgent):
    role = AgentRole.REVIEWER

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        return (
            f"System design:\n{json.dumps(state.get('architecture') or {}, indent=2)}\n\n"
            f"Generated files:\n{json.dumps(state.get('files', []), indent=2)}\n\n"
            "Produce the review as JSON."
        )

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or "verdict" not in payload:
            raise AgentExecutionError("Reviewer response missing 'verdict'")

        verdict = payload["verdict"]
        if verdict not in {v.value for v in ReviewVerdict}:
            raise AgentExecutionError(f"Reviewer produced invalid verdict: {verdict}")

        review = {
            "verdict": verdict,
            "findings": payload.get("findings", []),
            "summary": payload.get("summary", ""),
        }

        iterations = state.get("review_iterations", 0)
        patch: dict[str, Any] = {"review": review}

        if verdict == ReviewVerdict.CHANGES_REQUESTED.value:
            patch["review_iterations"] = iterations + 1
            patch["status"] = "coding"
        else:
            patch["status"] = "testing"

        return patch
