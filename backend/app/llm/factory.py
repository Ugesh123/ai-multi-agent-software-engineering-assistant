"""Factory for constructing the configured `LLMProvider`.

This is the single switch point between mock, Ollama, and Anthropic
providers. Nothing outside this module and `app.core.config` should know
that `OllamaProvider` / `AnthropicProvider` / `MockProvider` exist.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import LLMProviderKind, Settings, get_settings
from app.core.exceptions import ValidationError
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider is LLMProviderKind.MOCK:
        return MockProvider()

    if settings.llm_provider is LLMProviderKind.OLLAMA:
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    if settings.llm_provider is LLMProviderKind.ANTHROPIC:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            base_url=settings.anthropic_base_url,
            max_retries=settings.llm_max_retries,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(get_settings())


def build_provider_for_model(settings: Settings, model_spec: str) -> LLMProvider:
    """Build a provider for an explicit per-run model override.

    `model_spec` is either a bare model name (uses the app's currently
    configured provider TYPE, e.g. "llama3" while `MACA_LLM_PROVIDER=ollama`
    swaps just the model), or a "provider:model" spec (e.g.
    "anthropic:claude-sonnet-4-5") to switch provider for that one run.
    """

    if ":" in model_spec:
        provider_name, model_name = model_spec.split(":", 1)
    else:
        provider_name, model_name = settings.llm_provider.value, model_spec

    try:
        provider_kind = LLMProviderKind(provider_name)
    except ValueError as exc:
        raise ValidationError(f"Unknown provider '{provider_name}' in model spec '{model_spec}'") from exc

    if provider_kind is LLMProviderKind.OLLAMA:
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=model_name,
            timeout_seconds=settings.ollama_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if provider_kind is LLMProviderKind.ANTHROPIC:
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=model_name,
            base_url=settings.anthropic_base_url,
            max_retries=settings.llm_max_retries,
        )
    if provider_kind is LLMProviderKind.MOCK:
        return MockProvider()

    raise ValidationError(f"Unsupported provider '{provider_name}' in model spec '{model_spec}'")
