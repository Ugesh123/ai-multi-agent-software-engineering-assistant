"""SQLAlchemy ORM models.

The `AgentRun` aggregate has a rich nested shape (plan items, architecture,
generated files, review findings, messages, ...). Rather than fragmenting
that into a dozen join tables the run never queries independently, we
persist the nested structure as JSON alongside first-class relational
columns for everything the API needs to filter/sort/join on (id, status,
timestamps, project_id). This is a standard "aggregate root as document"
pattern for aggregates that are always loaded/saved as a whole.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import RunStatus


def _uuid() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    runs: Mapped[list["AgentRunORM"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ReferenceDocumentORM(Base):
    __tablename__ = "reference_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class DocumentChunkORM(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # "generated_file" (source_id = file path) or "reference_doc" (source_id = ReferenceDocumentORM.id)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(500), nullable=False)
    source_label: Mapped[str] = mapped_column(String(500), default="")
    chunk_index: Mapped[int] = mapped_column(default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class AgentRunORM(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    request: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=RunStatus.PENDING.value, nullable=False
    )
    parent_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(default=1)
    commit_message: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str | None] = mapped_column(String(200), default=None)
    plan: Mapped[list] = mapped_column(JSON, default=list)
    architecture: Mapped[dict | None] = mapped_column(JSON, default=None)
    files: Mapped[list] = mapped_column(JSON, default=list)
    review: Mapped[dict | None] = mapped_column(JSON, default=None)
    test_report: Mapped[dict | None] = mapped_column(JSON, default=None)
    documentation: Mapped[str] = mapped_column(Text, default="")
    messages: Mapped[list] = mapped_column(JSON, default=list)
    review_iterations: Mapped[int] = mapped_column(default=0)
    test_iterations: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    project: Mapped["ProjectORM"] = relationship(back_populates="runs")
