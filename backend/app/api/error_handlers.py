"""Central mapping from domain exceptions to HTTP responses.

Registered once in `app.main`; individual route handlers never need
try/except around domain calls -- they let `MacaError` subclasses
propagate and this module turns them into the right status code.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AgentExecutionError,
    LLMProviderError,
    MacaError,
    NotFoundError,
    RepositoryError,
    ValidationError,
    WorkflowError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_STATUS_MAP: dict[type[MacaError], int] = {
    NotFoundError: 404,
    ValidationError: 422,
    LLMProviderError: 502,
    AgentExecutionError: 502,
    WorkflowError: 409,
    RepositoryError: 500,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MacaError)
    async def handle_maca_error(request: Request, exc: MacaError) -> JSONResponse:
        status_code = _STATUS_MAP.get(type(exc), 500)
        if status_code >= 500:
            logger.error("Unhandled application error: %s", exc.message, exc_info=exc)
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"error": "Internal server error", "details": {}})
