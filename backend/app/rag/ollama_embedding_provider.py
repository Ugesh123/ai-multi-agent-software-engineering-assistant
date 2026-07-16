"""Production embedding provider: calls a local Ollama server's embedding
endpoint. Default model is `nomic-embed-text` -- pull it with
`ollama pull nomic-embed-text` alongside the main chat model."""

from __future__ import annotations

import httpx

from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.rag.base import EmbeddingProvider

logger = get_logger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for text in texts:
                try:
                    resp = await client.post(
                        f"{self._base_url}/api/embeddings",
                        json={"model": self._model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    embedding = data.get("embedding")
                    if not embedding:
                        raise LLMProviderError("Ollama returned an empty embedding")
                    vectors.append(embedding)
                except httpx.HTTPError as exc:
                    raise LLMProviderError(f"Ollama embedding request failed: {exc}") from exc

        return vectors

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
