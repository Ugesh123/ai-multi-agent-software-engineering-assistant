from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.api.schemas import HealthResponse
from app.core.container import Container

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    llm_healthy = await container.llm_provider.health_check()
    return HealthResponse(
        status="ok",
        llm_provider=container.settings.llm_provider.value,
        llm_healthy=llm_healthy,
    )
