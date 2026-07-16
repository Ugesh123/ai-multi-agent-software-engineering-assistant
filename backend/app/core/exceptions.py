"""Application exception hierarchy.

Every domain-level failure raises one of these instead of a bare
`Exception`, so the API layer can map errors to correct HTTP status codes
in one place (see `app.api.error_handlers`).
"""

from __future__ import annotations


class MacaError(Exception):
    """Base class for all application-raised errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(MacaError):
    """Raised when a requested entity does not exist."""


class ValidationError(MacaError):
    """Raised when input fails domain-level validation."""


class LLMProviderError(MacaError):
    """Raised when the underlying LLM backend fails or is unreachable."""


class AgentExecutionError(MacaError):
    """Raised when an agent node fails to produce a usable result."""


class WorkflowError(MacaError):
    """Raised for orchestration-level failures in the LangGraph workflow."""


class RepositoryError(MacaError):
    """Raised for persistence-layer failures."""
