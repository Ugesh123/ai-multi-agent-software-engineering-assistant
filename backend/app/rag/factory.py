"""Factory for constructing the configured `EmbeddingProvider`."""

from __future__ import annotations

from app.core.config import LLMProviderKind, Settings
from app.rag.base import EmbeddingProvider
from app.rag.mock_embedding_provider import MockEmbeddingProvider
from app.rag.ollama_embedding_provider import OllamaEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider is LLMProviderKind.MOCK:
        return MockEmbeddingProvider()

    # Embeddings currently only have a real (Ollama) and mock implementation;
    # any other configured provider kind falls back to Ollama's embedding
    # endpoint, since chat-completion providers like Anthropic don't expose
    # a comparable embeddings API in this app's supported feature set.
    return OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )
