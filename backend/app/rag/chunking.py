"""Splits text into overlapping chunks for embedding.

Kept deliberately simple (fixed-size character windows with overlap)
rather than a token-aware splitter -- appropriate for the scale of a
local single-user tool, and avoids pulling in a tokenizer dependency
just for chunk boundaries.
"""

from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split `text` into chunks of ~`chunk_size` chars with `overlap`
    chars shared between consecutive chunks, breaking on paragraph/line
    boundaries where possible to avoid mid-sentence cuts."""

    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Prefer breaking at the last paragraph or line break in range.
            break_point = text.rfind("\n\n", start, end)
            if break_point == -1 or break_point <= start:
                break_point = text.rfind("\n", start, end)
            if break_point != -1 and break_point > start:
                end = break_point

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks
