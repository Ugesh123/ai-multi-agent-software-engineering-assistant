"""Deterministic mock embedding provider for tests.

Produces hashed bag-of-words vectors: each word hashes into one of N
buckets, counts are normalized. This is NOT a semantic embedding, but it
is deterministic and preserves word-overlap similarity, which is enough
to test that `VectorStore` retrieval actually ranks more-relevant chunks
higher -- real semantic quality comes from `OllamaEmbeddingProvider` in
production.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.rag.base import EmbeddingProvider

_DIMENSIONS = 64
_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


def _hash_bucket(word: str) -> int:
    digest = hashlib.sha256(word.lower().encode()).digest()
    return int.from_bytes(digest[:4], "big") % _DIMENSIONS


class MockEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * _DIMENSIONS
        for word in _WORD_RE.findall(text):
            vector[_hash_bucket(word)] += 1.0

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    async def health_check(self) -> bool:
        return True
