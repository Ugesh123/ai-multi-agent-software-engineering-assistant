"""Alternate hosted-API LLM provider: Anthropic's Messages API.

Enables running the agent pipeline against a hosted model instead of (or
per-run, alongside) local Ollama inference. Requires `MACA_ANTHROPIC_API_KEY`
to be set; the model string is caller-supplied (see `app.llm.factory`) since
Anthropic's available model names change over time and this backend should
not hardcode an assumption about which are current -- callers should check
Anthropic's docs (https://docs.claude.com) for valid model strings.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = get_logger(__name__)

_API_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 8192


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.anthropic.com",
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        if not api_key:
            raise LLMProviderError("Anthropic provider requires an API key")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._max_tokens = max_tokens

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

    def _payload(self, messages: list[LLMMessage], temperature: float | None, stream: bool) -> dict:
        system_parts = [m.content for m in messages if m.role == "system"]
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        payload: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": turns,
            "stream": stream,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

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
                    resp = await client.post(
                        f"{self._base_url}/v1/messages", json=payload, headers=self._headers()
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
                    content = "".join(text_blocks)
                    if not content:
                        raise LLMProviderError("Anthropic returned an empty response")
                    return LLMResponse(content=content, model=self._model, raw=data)
                except (httpx.HTTPError, LLMProviderError, ValueError) as exc:
                    last_error = exc
                    logger.warning(
                        "Anthropic generate attempt %s/%s failed: %s",
                        attempt,
                        self._max_retries + 1,
                        exc,
                    )

        raise LLMProviderError(
            f"Anthropic request failed after {self._max_retries + 1} attempts: {last_error}"
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
                    "POST", f"{self._base_url}/v1/messages", json=payload, headers=self._headers()
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        chunk = json.loads(line[len("data: ") :])
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic streaming request failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/messages",
                    headers=self._headers(),
                    json={
                        "model": self._model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                # 200 = reachable+authorized; 4xx other than 401/403 still means "reachable".
                return resp.status_code < 500 and resp.status_code != 401 and resp.status_code != 403
        except httpx.HTTPError:
            return False
