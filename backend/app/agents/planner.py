"""Planner agent: turns a natural-language feature request into an ordered,
dependency-aware task plan that downstream agents execute against."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.domain.enums import AgentRole

_SYSTEM_PROMPT = """You are the Planner agent in a multi-agent software engineering system. [AGENT:PLANNER]

Your job is to break down a user's software request into a small, ordered list of
concrete, actionable implementation tasks. Do not write any code. Do not design the
architecture -- that is a different agent's job. Focus purely on WHAT needs to be
built, in what order, and what depends on what.

Respond with ONLY a JSON object of this exact shape, and nothing else:
{
  "items": [
    {"title": "short task title", "description": "1-2 sentence description", "order": 0, "depends_on": []}
  ]
}
"""


class PlannerAgent(BaseAgent):
    role = AgentRole.PLANNER

    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_user_prompt(self, state: dict[str, Any]) -> str:
        parts = [f"User request:\n{state['request']}"]

        existing_files = state.get("files") or []
        if existing_files:
            file_list = "\n".join(f"- {f['path']}" for f in existing_files)
            parts.append(
                "This is an incremental change to an EXISTING project with these files "
                f"already in place:\n{file_list}\n\n"
                "Plan only the tasks needed for the new request above; do not "
                "re-plan work for what already exists."
            )

        retrieved = state.get("retrieved_context") or []
        if retrieved:
            snippets = "\n\n".join(
                f"[{c['source_type']}: {c['source_label']}]\n{c['content']}" for c in retrieved
            )
            parts.append(
                "Relevant material retrieved from the project's reference "
                f"documents and existing code (use it to ground the plan, don't "
                f"just restate it):\n{snippets}"
            )

        parts.append("Produce the task plan as JSON.")
        return "\n\n".join(parts)

    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or "items" not in payload:
            raise AgentExecutionError("Planner response missing 'items' array")

        items = payload["items"]
        if not isinstance(items, list) or not items:
            raise AgentExecutionError("Planner produced an empty or invalid plan")

        normalized = []
        for idx, item in enumerate(items):
            normalized.append(
                {
                    "id": item.get("id") or f"task-{idx}",
                    "title": item.get("title", f"Task {idx}"),
                    "description": item.get("description", ""),
                    "order": item.get("order", idx),
                    "depends_on": item.get("depends_on", []),
                }
            )

        return {"plan": normalized, "status": "designing"}
