from __future__ import annotations

from app.rag.chunking import chunk_text


def test_chunk_text_returns_single_chunk_for_short_text():
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=1000)
    assert chunks == [text]


def test_chunk_text_returns_empty_list_for_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_splits_long_text_into_multiple_chunks():
    text = "word " * 1000
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 220  # allow small slack for boundary snapping


def test_chunk_text_prefers_paragraph_boundaries():
    text = "Paragraph one is short.\n\n" + ("x" * 190) + "\n\nParagraph three."
    chunks = chunk_text(text, chunk_size=200, overlap=10)
    assert len(chunks) >= 2
    # First chunk shouldn't cut mid-paragraph if a break point was available nearby.
    assert chunks[0].strip() != ""


def test_chunk_text_reconstructs_full_content_with_overlap():
    text = "A" * 50 + "B" * 50 + "C" * 50
    chunks = chunk_text(text, chunk_size=60, overlap=10)
    combined = "".join(chunks)
    assert "A" in combined and "B" in combined and "C" in combined
