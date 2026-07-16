"""LLM provider abstraction.

Every agent talks to `LLMProvider`, never to Ollama or any SDK directly.
This is what lets the whole multi-agent graph run against `MockProvider`
in CI/tests and against `OllamaProvider` in local/production use with
zero code changes elsewhere -- only `app.core.config.llm_provider` moves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(slots=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    model: str
    raw: dict | None = None


class LLMProvider(ABC):
    """Abstract chat-completion provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return a single complete response for the given conversation."""

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield response content incrementally, token-chunk by chunk."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and ready to serve."""
