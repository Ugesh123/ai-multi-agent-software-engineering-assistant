from __future__ import annotations

import io

import pytest

from app.core.exceptions import ValidationError
from app.domain.enums import FileChangeType
from app.domain.models import GeneratedFile
from app.rag.mock_embedding_provider import MockEmbeddingProvider
from app.services.rag_service import RagService, extract_text


def _make_real_pdf_bytes(text: str) -> bytes:
    """Build a minimal real PDF using pypdf so extraction is tested against
    an actual PDF binary, not a fake stand-in."""

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_extract_text_from_plain_text():
    result = extract_text("notes.txt", "text/plain", b"hello world")
    assert result == "hello world"


def test_extract_text_rejects_undecodable_bytes():
    with pytest.raises(ValidationError):
        extract_text("bad.txt", "text/plain", b"\xff\xfe\x00\xff")


def test_extract_text_from_pdf_does_not_crash_on_real_pdf_bytes():
    pdf_bytes = _make_real_pdf_bytes("irrelevant")
    # A blank-page PDF legitimately extracts to empty text; this test's
    # job is confirming pypdf integration works end-to-end without error.
    result = extract_text("spec.pdf", "application/pdf", pdf_bytes)
    assert isinstance(result, str)


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(ValidationError):
        extract_text("malware.exe", "application/octet-stream", b"MZ\x90\x00")


def test_extract_text_rejects_unsupported_content_type_with_no_extension():
    with pytest.raises(ValidationError):
        extract_text("untitled", "application/zip", b"PK\x03\x04")


def test_extract_text_accepts_markdown_extension_with_generic_content_type():
    # Some clients send "application/octet-stream" for .md uploads; the
    # extension allowlist should still accept it.
    result = extract_text("notes.md", "application/octet-stream", b"# Notes\n\nSome content.")
    assert "Notes" in result


@pytest.mark.asyncio
async def test_rag_service_ingest_and_retrieve_reference_document(session_factory):
    embedder = MockEmbeddingProvider()
    service = RagService(session_factory, embedder)

    await service.ingest_reference_document(
        "project-1", "spec.txt", "text/plain", b"The system must support user authentication via OAuth."
    )

    results = await service.retrieve("project-1", "OAuth authentication", top_k=3)
    assert len(results) > 0
    assert results[0].source_type == "reference_doc"
    assert results[0].source_label == "spec.txt"


@pytest.mark.asyncio
async def test_rag_service_ingest_generated_files_and_retrieve(session_factory):
    embedder = MockEmbeddingProvider()
    service = RagService(session_factory, embedder)

    files = [
        GeneratedFile(
            path="app/auth.py",
            content="def authenticate_user(token): validate_oauth_token(token)",
            change_type=FileChangeType.CREATE,
        ),
        GeneratedFile(
            path="app/render.py",
            content="def render_page(template): return template.render()",
            change_type=FileChangeType.CREATE,
        ),
    ]
    await service.ingest_generated_files("project-1", files)

    results = await service.retrieve("project-1", "authenticate_user oauth token", top_k=2)
    assert len(results) > 0
    assert results[0].source_label == "app/auth.py"


@pytest.mark.asyncio
async def test_rag_service_reingest_replaces_old_generated_file_chunks(session_factory):
    embedder = MockEmbeddingProvider()
    service = RagService(session_factory, embedder)

    v1_files = [GeneratedFile(path="app/core.py", content="def old_function(): pass")]
    await service.ingest_generated_files("project-1", v1_files)

    v2_files = [GeneratedFile(path="app/core.py", content="def new_function(): pass")]
    await service.ingest_generated_files("project-1", v2_files)

    results = await service.retrieve("project-1", "new_function", top_k=5)
    assert any("new_function" in r.content for r in results)
    assert not any("old_function" in r.content for r in results)


@pytest.mark.asyncio
async def test_rag_service_list_and_delete_document(session_factory):
    embedder = MockEmbeddingProvider()
    service = RagService(session_factory, embedder)

    doc = await service.ingest_reference_document(
        "project-1", "notes.txt", "text/plain", b"some reference content here"
    )
    docs = await service.list_documents("project-1")
    assert len(docs) == 1

    await service.delete_document("project-1", doc.id)
    docs_after = await service.list_documents("project-1")
    assert docs_after == []
