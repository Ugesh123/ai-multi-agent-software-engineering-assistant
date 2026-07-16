"""Architect agent: turns the task plan into a concrete system design --
components, responsibilities, tech choices, and file layout."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.domain.enums import AgentRole

_SYSTEM_PROMPT = """You are the Architect agent in a multi-agent software engineering system. [AGENT:ARCHITECT]

You receive an ordered task plan and must produce a concrete, minimal software design:
the components/modules needed, each one's single responsibility, the public interfaces
they expose, their dependencies on each other, key technology choices, and the exact
file layout the Coder agent should create. Favor simplicity: the smallest design that
correctly satisfies the plan. Do not write implementation code.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "summary": "1-3 sentence design summary",
  "components": [
    {"name": "component_name", "responsibility": "...", "interfaces": ["func(args) -> ret"], "dependencies": []}
  ],
  "tech_choices": {"language": "python", "test_framework": "pytest"},
  "file_layout": ["relative/path/one.py", "relative/path/two.py"]
}
"""


class ArchitectAgent(BaseAgent):
    role = AgentRole.ARCHITECT

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        plan = json.dumps(state.get("plan", []), indent=2)
        parts = [f"User request:\n{state['request']}", f"Task plan:\n{plan}"]

        existing_architecture = state.get("architecture")
        if existing_architecture:
            parts.append(
                "This is an incremental change to an EXISTING project with this "
                f"prior design -- extend or adjust it, don't discard it unnecessarily:\n"
                f"{json.dumps(existing_architecture, indent=2)}"
            )

        retrieved = state.get("retrieved_context") or []
        if retrieved:
            snippets = "\n\n".join(
                f"[{c['source_type']}: {c['source_label']}]\n{c['content']}" for c in retrieved
            )
            parts.append(
                f"Relevant material retrieved from reference documents and existing "
                f"code:\n{snippets}"
            )

        parts.append("Produce the system design as JSON.")
        return "\n\n".join(parts)

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or "components" not in payload:
            raise AgentExecutionError("Architect response missing 'components'")

        architecture = {
            "summary": payload.get("summary", ""),
            "components": payload.get("components", []),
            "tech_choices": payload.get("tech_choices", {}),
            "file_layout": payload.get("file_layout", []),
        }
        return {"architecture": architecture, "status": "coding"}
