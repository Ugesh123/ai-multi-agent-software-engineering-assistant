"""Base class for all LangGraph agent nodes.

Each concrete agent (Planner, Architect, Coder, Reviewer, Tester,
Documentation) subclasses `BaseAgent`, supplies a system prompt and a
user-prompt builder, and gets JSON-response parsing, retries, structured
logging, and transcript recording for free. This keeps every agent file
focused purely on *what* it asks the model, not *how* it talks to it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.exceptions import AgentExecutionError, LLMProviderError
from app.core.logging import get_logger
from app.domain.enums import AgentRole
from app.llm.base import LLMMessage, LLMProvider
from app.llm.json_utils import extract_json


class BaseAgent(ABC):
    """Template-method base class for a single LangGraph agent node."""

    role: AgentRole

    def __init__(self, llm: LLMProvider, *, max_attempts: int = 2) -> None:
        self._llm = llm
        self._max_attempts = max_attempts
        self._logger = get_logger(f"agent.{self.role.value}")

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt. Must embed `[AGENT:<ROLE>]` for the mock provider."""

    @abstractmethod
    def build_user_prompt(self, state: dict[str, Any]) -> str:
        """Build the user-turn prompt from the current workflow state."""

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute this agent against the given state and return a state patch."""

        self._logger.info("Starting %s agent for run_id=%s", self.role.value, state.get("run_id"))
        user_prompt = self.build_user_prompt(state)
        messages = [
            LLMMessage(role="system", content=self.system_prompt()),
            LLMMessage(role="user", content=user_prompt),
        ]

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._llm.generate(messages)
                payload = extract_json(response.content)
                patch = self.parse_response(payload, state)
                patch["messages"] = [self._transcript_entry(self._summarize(payload))]
                self._logger.info(
                    "%s agent completed successfully (attempt %s)", self.role.value, attempt
                )
                return patch
            except (LLMProviderError, AgentExecutionError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                self._logger.warning(
                    "%s agent attempt %s/%s failed: %s",
                    self.role.value,
                    attempt,
                    self._max_attempts,
                    exc,
                )

        raise AgentExecutionError(
            f"{self.role.value} agent failed after {self._max_attempts} attempts: {last_error}"
        )

    @abstractmethod
    def parse_response(self, payload: dict | list, state: dict[str, Any]) -> dict[str, Any]:
        """Convert the parsed JSON payload into a partial `WorkflowState` patch."""

    def _summarize(self, payload: dict | list) -> str:
        return f"{self.role.value} produced output with keys: {self._keys(payload)}"

    @staticmethod
    def _keys(payload: dict | list) -> str:
        if isinstance(payload, dict):
            return ", ".join(payload.keys())
        return f"list[{len(payload)}]"

    def _transcript_entry(self, content: str) -> dict:
        return {
            "id": str(uuid4()),
            "role": self.role.value,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
