"""Coder agent: generates the actual source files from the architecture,
and revises them when the Reviewer or Tester agents request changes."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.domain.enums import AgentRole, FileChangeType

_SYSTEM_PROMPT = """You are the Coder agent in a multi-agent software engineering system. [AGENT:CODER]

You receive a system design (and, on revision passes, review findings, failing test
output, and/or a list of an EXISTING project's files) and must produce complete,
runnable, idiomatic source files that satisfy it. Every file you output must be
complete -- no "// ... rest of implementation" placeholders, no TODOs, no stubs.
Include tests where the design calls for a test framework. Follow standard style
conventions for the target language.

IMPORTANT: only include files you are CREATING, UPDATING, or DELETING in your
response. Do not repeat unchanged existing files -- the system merges your output
with the existing file set automatically, keyed by path.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "files": [
    {"path": "relative/path.py", "change_type": "create", "language": "python", "content": "full file contents"}
  ]
}
change_type must be one of: create, update, delete. For delete, content may be empty.
"""


class CoderAgent(BaseAgent):
    role = AgentRole.CODER

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        parts = [
            f"User request:\n{state['request']}",
            f"System design:\n{json.dumps(state.get('architecture') or {}, indent=2)}",
        ]

        existing_files = state.get("files") or []
        if existing_files:
            parts.append(
                "Existing project files (for context -- only return files you "
                f"CREATE, UPDATE, or DELETE; unchanged files are kept automatically):\n"
                f"{json.dumps(existing_files, indent=2)}"
            )

        review = state.get("review")
        if review and review.get("verdict") == "changes_requested":
            parts.append(
                "The Reviewer requested changes. Address every finding below and "
                f"return only the corrected files:\n{json.dumps(review, indent=2)}"
            )

        test_report = state.get("test_report")
        if test_report and test_report.get("verdict") == "failed":
            parts.append(
                "The Tester reported failing tests. Fix the implementation so all "
                f"tests pass, and return only the corrected files:\n"
                f"{json.dumps(test_report, indent=2)}"
            )

        parts.append("Produce only the files you are creating, updating, or deleting, as JSON.")
        return "\n\n".join(parts)

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or "files" not in payload:
            raise AgentExecutionError("Coder response missing 'files'")

        changed_files = payload["files"]
        if not isinstance(changed_files, list) or not changed_files:
            raise AgentExecutionError("Coder produced no files")

        valid_change_types = {c.value for c in FileChangeType}
        normalized = []
        for f in changed_files:
            change_type = f.get("change_type", "create")
            if change_type not in valid_change_types:
                change_type = "create"
            normalized.append(
                {
                    "path": f["path"],
                    "content": f.get("content", ""),
                    "change_type": change_type,
                    "language": f.get("language", "text"),
                }
            )

        # Merge the Coder's (possibly partial) output into the existing file set,
        # keyed by path, so a revision pass only needs to describe what changed
        # rather than repeating the entire codebase back verbatim every time.
        merged: dict[str, dict] = {f["path"]: f for f in state.get("files") or []}
        for f in normalized:
            if f["change_type"] == FileChangeType.DELETE.value:
                merged.pop(f["path"], None)
            else:
                merged[f["path"]] = f

        merged_files = sorted(merged.values(), key=lambda f: f["path"])
        if not merged_files:
            raise AgentExecutionError("Coder's changes left the project with no files")

        return {"files": merged_files, "status": "reviewing"}
