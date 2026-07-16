"""Application-wide logging configuration.

Provides a single `configure_logging()` entry point (called once at process
startup) and a `get_logger(name)` helper so every module gets a consistently
formatted, correctly leveled logger instead of ad-hoc `print()` calls.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import get_settings

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Minimal dependency-free JSON log formatter for production use."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    """Idempotently configure the root logger for the whole process."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(stream=sys.stdout)
    if settings.log_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers unless we're debugging.
    for noisy in ("httpx", "httpcore", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(
            logging.WARNING if not settings.debug else logging.INFO
        )

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring logging on first use."""

    configure_logging()
    return logging.getLogger(name)
