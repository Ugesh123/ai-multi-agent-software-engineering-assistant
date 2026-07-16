"""Utilities for robustly extracting JSON from raw LLM text output.

Local models (Qwen3 via Ollama included) frequently wrap JSON in markdown
fences, prose preambles ("Here is the plan:"), or trailing commentary.
This module makes JSON extraction resilient to all of that instead of
naively calling `json.loads` on the raw string and failing.
"""

from __future__ import annotations

import json
import re

from app.core.exceptions import LLMProviderError

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict | list:
    """Extract and parse the first valid JSON object/array found in `text`.

    Raises:
        LLMProviderError: if no valid JSON payload can be located.
    """

    candidates: list[str] = []

    fence_match = _FENCE_RE.search(text)
    if fence_match:
        candidates.append(fence_match.group(1))

    candidates.append(text.strip())

    first_obj = text.find("{")
    first_arr = text.find("[")
    starts = [p for p in (first_obj, first_arr) if p != -1]
    if starts:
        start = min(starts)
        end_obj = text.rfind("}")
        end_arr = text.rfind("]")
        end = max(end_obj, end_arr)
        if end > start:
            candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue

    raise LLMProviderError(
        "Could not extract valid JSON from LLM response",
        details={"raw_response": text[:2000]},
    )
