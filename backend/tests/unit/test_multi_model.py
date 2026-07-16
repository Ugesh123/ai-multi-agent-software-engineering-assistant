from __future__ import annotations

import pytest

from app.core.config import LLMProviderKind, get_settings
from app.core.exceptions import LLMProviderError, ValidationError
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import build_provider_for_model
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider


@pytest.fixture
def settings():
    get_settings.cache_clear()
    s = get_settings()
    s.llm_provider = LLMProviderKind.OLLAMA
    s.ollama_model = "qwen3:14b"
    s.anthropic_api_key = "test-key"
    return s


def test_bare_model_name_uses_configured_provider_type(settings):
    provider = build_provider_for_model(settings, "llama3")
    assert isinstance(provider, OllamaProvider)


def test_prefixed_model_spec_switches_provider(settings):
    provider = build_provider_for_model(settings, "anthropic:claude-sonnet-4-5")
    assert isinstance(provider, AnthropicProvider)


def test_prefixed_ollama_spec_explicit(settings):
    provider = build_provider_for_model(settings, "ollama:codellama")
    assert isinstance(provider, OllamaProvider)


def test_mock_prefixed_spec(settings):
    provider = build_provider_for_model(settings, "mock:anything")
    assert isinstance(provider, MockProvider)


def test_unknown_provider_prefix_raises(settings):
    with pytest.raises(ValidationError):
        build_provider_for_model(settings, "unknown-provider:some-model")


def test_anthropic_provider_requires_api_key():
    with pytest.raises(LLMProviderError):
        AnthropicProvider(api_key="", model="claude-sonnet-4-5")


def test_anthropic_provider_builds_correct_payload():
    from app.llm.base import LLMMessage

    provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello"),
    ]
    payload = provider._payload(messages, temperature=0.5, stream=False)

    assert payload["model"] == "claude-sonnet-4-5"
    assert payload["system"] == "You are a helpful assistant."
    assert payload["messages"] == [{"role": "user", "content": "Hello"}]
    assert payload["temperature"] == 0.5
    assert payload["stream"] is False


def test_anthropic_provider_headers_include_api_key():
    provider = AnthropicProvider(api_key="secret-key-123", model="claude-sonnet-4-5")
    headers = provider._headers()
    assert headers["x-api-key"] == "secret-key-123"
    assert "anthropic-version" in headers
