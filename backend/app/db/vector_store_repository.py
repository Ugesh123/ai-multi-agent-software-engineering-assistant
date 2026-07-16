"""Persistence for RAG: reference documents and their/generated-files'
embedded chunks, plus cosine-similarity retrieval.

Cosine similarity is computed in Python over chunks loaded for a single
project (not a global index) -- appropriate at the scale of one local
project's files and a handful of reference docs; no vector-DB dependency
needed.
"""

from __future__ import annotations

import math

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import DocumentChunkORM, ReferenceDocumentORM
from app.domain.models import ReferenceDocument, RetrievedChunk


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_generated_file_chunks(
        self, project_id: str, chunks: list[dict]
    ) -> None:
        """Replace all `generated_file`-sourced chunks for a project with a
        fresh set, called after every completed run so retrieval always
        reflects the latest version's code, not stale prior versions."""

        await self._session.execute(
            delete(DocumentChunkORM).where(
                DocumentChunkORM.project_id == project_id,
                DocumentChunkORM.source_type == "generated_file",
            )
        )
        for chunk in chunks:
            self._session.add(
                DocumentChunkORM(
                    project_id=project_id,
                    source_type="generated_file",
                    source_id=chunk["source_id"],
                    source_label=chunk["source_id"],
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    embedding=chunk["embedding"],
                )
            )
        await self._session.flush()

    async def add_reference_document(
        self, document: ReferenceDocument, chunks: list[dict]
    ) -> ReferenceDocument:
        row = ReferenceDocumentORM(
            id=document.id,
            project_id=document.project_id,
            filename=document.filename,
            content_type=document.content_type,
            extracted_text=document.extracted_text,
            created_at=document.created_at,
        )
        self._session.add(row)

        for chunk in chunks:
            self._session.add(
                DocumentChunkORM(
                    project_id=document.project_id,
                    source_type="reference_doc",
                    source_id=document.id,
                    source_label=document.filename,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    embedding=chunk["embedding"],
                )
            )
        await self._session.flush()
        return document

    async def list_reference_documents(self, project_id: str) -> list[ReferenceDocument]:
        result = await self._session.execute(
            select(ReferenceDocumentORM)
            .where(ReferenceDocumentORM.project_id == project_id)
            .order_by(ReferenceDocumentORM.created_at.desc())
        )
        return [
            ReferenceDocument(
                id=row.id,
                project_id=row.project_id,
                filename=row.filename,
                content_type=row.content_type,
                extracted_text=row.extracted_text,
                created_at=row.created_at,
            )
            for row in result.scalars().all()
        ]

    async def delete_reference_document(self, project_id: str, document_id: str) -> None:
        row = await self._session.get(ReferenceDocumentORM, document_id)
        if row is None or row.project_id != project_id:
            raise NotFoundError(f"Reference document {document_id} not found")

        await self._session.execute(
            delete(DocumentChunkORM).where(
                DocumentChunkORM.project_id == project_id,
                DocumentChunkORM.source_type == "reference_doc",
                DocumentChunkORM.source_id == document_id,
            )
        )
        await self._session.delete(row)
        await self._session.flush()

    async def search(
        self, project_id: str, query_embedding: list[float], top_k: int = 5
    ) -> list[RetrievedChunk]:
        result = await self._session.execute(
            select(DocumentChunkORM).where(DocumentChunkORM.project_id == project_id)
        )
        rows = result.scalars().all()

        scored = [
            (row, _cosine_similarity(query_embedding, row.embedding))
            for row in rows
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        return [
            RetrievedChunk(
                source_type=row.source_type,
                source_label=row.source_label,
                content=row.content,
                score=score,
            )
            for row, score in scored[:top_k]
            if score > 0
        ]
