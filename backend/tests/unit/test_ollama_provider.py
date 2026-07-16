"""Tests for OllamaProvider's retry logic, using httpx.MockTransport so no
real network/Ollama server is needed.

Covers the regression found in production: an overly broad `except
ValueError` in the retry loop was silently retrying (and thus masking)
unrelated bugs -- specifically a third-party `ValueError` raised deep in
httpx/httpcore/anyio's connection layer on Windows -- as if they were
ordinary transient failures.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import LLMProviderError
from app.llm.base import LLMMessage
from app.llm.ollama_provider import OllamaProvider

pytestmark = pytest.mark.asyncio


@pytest.fixture
def patch_async_client(monkeypatch):
    """Patch httpx.AsyncClient so every construction inside OllamaProvider
    uses the given transport instead of real sockets."""

    def _apply(transport):
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            return original_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    return _apply


async def test_generate_succeeds_on_first_try(patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "hello"}})

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model")

    response = await provider.generate([LLMMessage(role="user", content="hi")])
    assert response.content == "hello"


async def test_generate_retries_on_malformed_json_then_succeeds(patch_async_client):
    """A JSONDecodeError (genuinely transient -- e.g. a truncated response)
    should be retried."""

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, content=b"not valid json{{{")
        return httpx.Response(200, json={"message": {"content": "recovered"}})

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model", max_retries=2)

    response = await provider.generate([LLMMessage(role="user", content="hi")])
    assert response.content == "recovered"
    assert calls["n"] == 2


async def test_generate_retries_on_http_error_then_succeeds(patch_async_client):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"message": {"content": "ok"}})

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model", max_retries=2)

    response = await provider.generate([LLMMessage(role="user", content="hi")])
    assert response.content == "ok"
    assert calls["n"] == 2


async def test_generate_exhausts_retries_and_raises_llm_provider_error(patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model", max_retries=2)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate([LLMMessage(role="user", content="hi")])
    assert "3 attempts" in str(exc_info.value)


async def test_generate_does_not_retry_or_mask_unrelated_value_error(monkeypatch):
    """Regression test: an arbitrary ValueError raised inside the request
    (simulating the real-world httpx/httpcore/anyio ExceptionGroup bug seen
    on Windows) must propagate immediately on the FIRST attempt, not be
    silently retried and disguised as a generic connection failure."""

    call_count = {"n": 0}

    class ExplodingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            # Reproduces the exact real-world failure: CPython's own
            # ExceptionGroup constructor raises this when given an empty
            # exception list, deep inside anyio's connection internals.
            raise ValueError("second argument (exceptions) must be a non-empty sequence")

    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = ExplodingTransport()
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model", max_retries=2)

    with pytest.raises(ValueError, match="non-empty sequence"):
        await provider.generate([LLMMessage(role="user", content="hi")])

    # The critical assertion: exactly ONE attempt was made. The old broad
    # `except ValueError` would have retried this 3 times (max_retries=2)
    # before raising a generic, misleading LLMProviderError -- masking the
    # real bug and wasting up to 3x the configured timeout.
    assert call_count["n"] == 1


async def test_generate_empty_content_response_is_retried(patch_async_client):
    """An empty `content` field raises LLMProviderError internally, which
    IS a case we understand and should retry."""

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"message": {"content": ""}})
        return httpx.Response(200, json={"message": {"content": "recovered"}})

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model", max_retries=2)

    response = await provider.generate([LLMMessage(role="user", content="hi")])
    assert response.content == "recovered"
    assert calls["n"] == 2


async def test_health_check_true_on_200(patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model")
    assert await provider.health_check() is True


async def test_health_check_false_on_connection_error(patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    patch_async_client(httpx.MockTransport(handler))
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="test-model")
    assert await provider.health_check() is False
