"""Builds an in-memory ZIP archive of a completed run's generated files.

Kept separate from `WorkflowService` because packaging is a distinct
responsibility (pure transformation, no persistence, no LLM calls) with
its own dedicated unit tests.
"""

from __future__ import annotations

import io
import posixpath
import zipfile

from app.core.logging import get_logger
from app.domain.models import AgentRun

logger = get_logger(__name__)


def _is_safe_archive_path(path: str) -> bool:
    """Reject paths that could "zip-slip" out of the extraction directory
    on whatever tool a user later extracts this archive with: absolute
    paths, `..` segments, and Windows drive letters/backslashes."""

    if not path or path.startswith("/") or path.startswith("\\"):
        return False
    if ":" in path:  # e.g. "C:\\..." on Windows
        return False
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if normalized.startswith("..") or normalized.startswith("/"):
        return False
    return True


def build_project_zip(run: AgentRun) -> bytes:
    """Return the bytes of a ZIP archive containing every non-deleted
    generated file plus a README.md (from the Documentation agent's
    output, if present)."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in run.files:
            change_type = file.change_type_value
            if change_type == "delete":
                continue
            if not _is_safe_archive_path(file.path):
                logger.warning("Skipping file with unsafe archive path: %s", file.path)
                continue
            archive.writestr(file.path, file.content)

        if run.documentation and not any(f.path.upper() == "README.MD" for f in run.files):
            archive.writestr("README.md", run.documentation)

    buffer.seek(0)
    return buffer.getvalue()
