"""Production LLM provider: talks to a local Ollama server.

This is the default provider (`app.core.config.llm_provider = ollama`).
It requires `ollama serve` running locally with the configured model
pulled (e.g. `ollama pull qwen3:14b`) -- nothing else changes in the
application when switching from mock to this provider.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    def _payload(
        self, messages: list[LLMMessage], temperature: float | None, stream: bool
    ) -> dict:
        return {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature if temperature is not None else 0.2},
        }

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
    ) -> LLMResponse:
        payload = self._payload(messages, temperature, stream=False)
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(1, self._max_retries + 2):
                try:
                    resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    if not content:
                        raise LLMProviderError("Ollama returned an empty response")
                    return LLMResponse(content=content, model=self._model, raw=data)
                # Deliberately narrow: only retry failures we understand and can
                # sensibly recover from (HTTP/connection errors, malformed JSON
                # in Ollama's response). A bare `except ValueError` here would
                # also silently swallow-and-retry unrelated bugs -- e.g. a
                # third-party ValueError raised deep in httpx/httpcore/anyio's
                # connection layer (seen in practice on Windows, where
                # "localhost" resolves to both 127.0.0.1 and ::1 and a
                # happy-eyeballs cancellation race can raise
                # `ValueError: second argument (exceptions) must be a
                # non-empty sequence` from CPython's own ExceptionGroup
                # constructor). That kind of bug should surface immediately
                # with its real traceback, not get masked as three identical
                # "Ollama generate attempt" warnings before an unhelpful
                # aggregate error. See app.core.config.ollama_base_url, which
                # defaults to 127.0.0.1 rather than "localhost" for the same
                # reason: avoid triggering the ambiguous dual-stack lookup at
                # all rather than merely tolerating its failure mode.
                except (httpx.HTTPError, LLMProviderError, json.JSONDecodeError) as exc:
                    last_error = exc
                    logger.warning(
                        "Ollama generate attempt %s/%s failed: %s",
                        attempt,
                        self._max_retries + 1,
                        exc,
                    )

        raise LLMProviderError(
            f"Ollama request failed after {self._max_retries + 1} attempts: {last_error}"
        ) from last_error

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        piece = chunk.get("message", {}).get("content", "")
                        if piece:
                            yield piece
                        if chunk.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama streaming request failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
