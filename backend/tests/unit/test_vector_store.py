from __future__ import annotations

import pytest

from app.db.vector_store_repository import VectorStoreRepository
from app.domain.models import ReferenceDocument
from app.rag.mock_embedding_provider import MockEmbeddingProvider

pytestmark = pytest.mark.asyncio


async def test_mock_embedding_provider_is_deterministic():
    provider = MockEmbeddingProvider()
    v1 = await provider.embed(["hello world"])
    v2 = await provider.embed(["hello world"])
    assert v1 == v2


async def test_mock_embedding_provider_similar_text_higher_similarity():
    import math

    provider = MockEmbeddingProvider()
    [a, b, c] = await provider.embed(
        [
            "the quick brown fox jumps over the lazy dog",
            "a quick brown fox jumps over a lazy dog",  # similar to a
            "quantum entanglement in superconducting circuits",  # unrelated
        ]
    )

    def cosine(x, y):
        dot = sum(p * q for p, q in zip(x, y))
        return dot / (math.sqrt(sum(p * p for p in x)) * math.sqrt(sum(q * q for q in y)))

    sim_similar = cosine(a, b)
    sim_different = cosine(a, c)
    assert sim_similar > sim_different


async def test_vector_store_search_ranks_relevant_generated_file_chunk_first(db_session):
    repo = VectorStoreRepository(db_session)
    embedder = MockEmbeddingProvider()

    chunks_content = [
        "def double(x): return x * 2  # doubling helper function",
        "class UnrelatedWidget: pass  # some unrelated UI widget code",
    ]
    embeddings = await embedder.embed(chunks_content)

    await repo.replace_generated_file_chunks(
        "project-1",
        [
            {"source_id": "app/core.py", "chunk_index": 0, "content": chunks_content[0], "embedding": embeddings[0]},
            {"source_id": "app/widget.py", "chunk_index": 0, "content": chunks_content[1], "embedding": embeddings[1]},
        ],
    )
    await db_session.commit()

    [query_embedding] = await embedder.embed(["doubling helper function"])
    results = await repo.search("project-1", query_embedding, top_k=2)

    assert results[0].source_label == "app/core.py"


async def test_vector_store_reference_document_lifecycle(db_session):
    repo = VectorStoreRepository(db_session)
    embedder = MockEmbeddingProvider()

    doc = ReferenceDocument(
        project_id="project-1", filename="spec.md", extracted_text="A product spec about widgets"
    )
    [embedding] = await embedder.embed([doc.extracted_text])
    await repo.add_reference_document(
        doc, [{"chunk_index": 0, "content": doc.extracted_text, "embedding": embedding}]
    )
    await db_session.commit()

    docs = await repo.list_reference_documents("project-1")
    assert len(docs) == 1
    assert docs[0].filename == "spec.md"

    await repo.delete_reference_document("project-1", doc.id)
    await db_session.commit()

    docs_after = await repo.list_reference_documents("project-1")
    assert docs_after == []


async def test_vector_store_search_isolated_per_project(db_session):
    repo = VectorStoreRepository(db_session)
    embedder = MockEmbeddingProvider()

    [embedding] = await embedder.embed(["database code"])
    await repo.replace_generated_file_chunks(
        "project-a",
        [{"source_id": "a.py", "chunk_index": 0, "content": "database code", "embedding": embedding}],
    )
    await db_session.commit()

    [query_embedding] = await embedder.embed(["database code"])
    results_a = await repo.search("project-a", query_embedding, top_k=5)
    results_b = await repo.search("project-b", query_embedding, top_k=5)

    assert len(results_a) == 1
    assert len(results_b) == 0


async def test_replace_generated_file_chunks_is_idempotent_per_project(db_session):
    repo = VectorStoreRepository(db_session)
    embedder = MockEmbeddingProvider()

    [e1] = await embedder.embed(["version one content"])
    await repo.replace_generated_file_chunks(
        "project-1", [{"source_id": "a.py", "chunk_index": 0, "content": "version one content", "embedding": e1}]
    )
    await db_session.commit()

    [e2] = await embedder.embed(["version two content"])
    await repo.replace_generated_file_chunks(
        "project-1", [{"source_id": "a.py", "chunk_index": 0, "content": "version two content", "embedding": e2}]
    )
    await db_session.commit()

    [query_embedding] = await embedder.embed(["version two content"])
    results = await repo.search("project-1", query_embedding, top_k=5)
    # Only the latest version's chunk should exist -- old one was replaced, not appended.
    assert len(results) == 1
    assert results[0].content == "version two content"
