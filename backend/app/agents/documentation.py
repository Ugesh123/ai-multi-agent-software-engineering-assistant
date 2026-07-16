"""Documentation agent: generates the final README for the project once
the code has been reviewed and its tests pass."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.domain.enums import AgentRole

_SYSTEM_PROMPT = """You are the Documentation agent in a multi-agent software engineering system. [AGENT:DOCUMENTATION]

You receive the original request, the system design, and the final generated files.
Write a clear, complete README in Markdown: what the project does, how it's
structured, how to install/run it, and how to run its tests. Be accurate to the
actual generated files -- do not invent commands or files that don't exist.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "readme": "full README.md content as a markdown string"
}
"""


class DocumentationAgent(BaseAgent):
    role = AgentRole.DOCUMENTATION

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        return (
            f"User request:\n{state['request']}\n\n"
            f"System design:\n{json.dumps(state.get('architecture') or {}, indent=2)}\n\n"
            f"Generated file paths:\n{[f['path'] for f in state.get('files', [])]}\n\n"
            "Produce the README as JSON."
        )

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or "readme" not in payload:
            raise AgentExecutionError("Documentation response missing 'readme'")

        return {"documentation": payload["readme"], "status": "completed"}
