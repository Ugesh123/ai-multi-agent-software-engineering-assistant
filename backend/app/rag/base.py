"""Embedding provider abstraction for RAG.

Mirrors `app.llm.base.LLMProvider`: agents/services depend on this
interface, never on Ollama or any SDK directly, so `MockEmbeddingProvider`
can drive tests while `OllamaEmbeddingProvider` (default, real, local) runs
in production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""

    @abstractmethod
    async def health_check(self) -> bool: ...
