from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.api.schemas import ModelInfo, ModelListResponse
from app.core.config import LLMProviderKind
from app.core.container import Container

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models(container: Container = Depends(get_container)) -> ModelListResponse:
    """List models available for per-run selection. For the Ollama
    provider, queries the local Ollama server's `/api/tags`. Always
    includes the currently configured default."""

    settings = container.settings
    models: list[ModelInfo] = []

    if settings.llm_provider is LLMProviderKind.OLLAMA:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                for entry in data.get("models", []):
                    name = entry.get("name") or entry.get("model")
                    if name:
                        models.append(ModelInfo(name=name, provider="ollama"))
        except httpx.HTTPError:
            pass  # Ollama unreachable -- fall back to just the configured default below.

    if not any(m.name == settings.ollama_model for m in models):
        models.insert(0, ModelInfo(name=settings.ollama_model, provider="ollama"))

    if settings.anthropic_model:
        models.append(ModelInfo(name=f"anthropic:{settings.anthropic_model}", provider="anthropic"))

    if settings.llm_provider is LLMProviderKind.OLLAMA:
        current_default = settings.ollama_model
    elif settings.llm_provider is LLMProviderKind.ANTHROPIC:
        current_default = settings.anthropic_model
    else:
        current_default = "mock"

    return ModelListResponse(models=models, current_default=current_default)
