"""RAG service: ingests both user-uploaded reference documents and a
project's own generated files into the vector store, and retrieves the
most relevant chunks for a query. This is what lets agents ground their
plans/designs in an uploaded spec AND in the project's existing code.
"""

from __future__ import annotations

import io

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.db.base import session_scope
from app.db.vector_store_repository import VectorStoreRepository
from app.domain.models import GeneratedFile, ReferenceDocument, RetrievedChunk
from app.rag.base import EmbeddingProvider
from app.rag.chunking import chunk_text

logger = get_logger(__name__)

_SUPPORTED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
}

_SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}


def _validate_upload_type(filename: str, content_type: str) -> None:
    """Reject unsupported file types before any parsing is attempted, with
    a clear error, rather than silently attempting UTF-8 decode on
    arbitrary binary content (images, archives, executables, ...)."""

    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in _SUPPORTED_EXTENSIONS and content_type not in _SUPPORTED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported file type for '{filename}' (content_type={content_type!r}). "
            f"Supported: .txt, .md, .pdf"
        )


def extract_text(filename: str, content_type: str, raw_bytes: bytes) -> str:
    """Extract plain text from an uploaded reference document."""

    _validate_upload_type(filename, content_type)

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency always installed
            raise ValidationError("PDF support requires the 'pypdf' package") from exc

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"Could not decode '{filename}' as UTF-8 text") from exc


class RagService:
    def __init__(self, session_factory: async_sessionmaker, embedder: EmbeddingProvider) -> None:
        self._session_factory = session_factory
        self._embedder = embedder

    async def ingest_reference_document(
        self, project_id: str, filename: str, content_type: str, raw_bytes: bytes
    ) -> ReferenceDocument:
        if len(raw_bytes) > 10 * 1024 * 1024:
            raise ValidationError("Reference document exceeds the 10MB size limit")

        text = extract_text(filename, content_type, raw_bytes)
        if not text.strip():
            raise ValidationError(f"No extractable text found in '{filename}'")

        document = ReferenceDocument(
            project_id=project_id,
            filename=filename,
            content_type=content_type or "text/plain",
            extracted_text=text,
        )

        chunks = chunk_text(text)
        embeddings = await self._embedder.embed(chunks)
        chunk_records = [
            {"chunk_index": i, "content": chunk, "embedding": vector}
            for i, (chunk, vector) in enumerate(zip(chunks, embeddings))
        ]

        async with session_scope(self._session_factory) as session:
            repository = VectorStoreRepository(session)
            return await repository.add_reference_document(document, chunk_records)

    async def ingest_generated_files(self, project_id: str, files: list[GeneratedFile]) -> None:
        """Re-index a project's current generated files. Called after every
        completed run so retrieval always reflects the latest version."""

        all_chunks: list[dict] = []
        chunk_texts: list[str] = []

        for file in files:
            pieces = chunk_text(file.content)
            for i, piece in enumerate(pieces):
                all_chunks.append({"source_id": file.path, "chunk_index": i})
                chunk_texts.append(piece)

        async with session_scope(self._session_factory) as session:
            repository = VectorStoreRepository(session)
            if not chunk_texts:
                await repository.replace_generated_file_chunks(project_id, [])
                return

            embeddings = await self._embedder.embed(chunk_texts)
            for record, text, vector in zip(all_chunks, chunk_texts, embeddings):
                record["content"] = text
                record["embedding"] = vector

            await repository.replace_generated_file_chunks(project_id, all_chunks)

    async def list_documents(self, project_id: str) -> list[ReferenceDocument]:
        async with session_scope(self._session_factory) as session:
            repository = VectorStoreRepository(session)
            return await repository.list_reference_documents(project_id)

    async def delete_document(self, project_id: str, document_id: str) -> None:
        async with session_scope(self._session_factory) as session:
            repository = VectorStoreRepository(session)
            await repository.delete_reference_document(project_id, document_id)

    async def retrieve(self, project_id: str, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        [query_embedding] = await self._embedder.embed([query])
        async with session_scope(self._session_factory) as session:
            repository = VectorStoreRepository(session)
            return await repository.search(project_id, query_embedding, top_k)
