from __future__ import annotations

import pytest

from app.core.exceptions import LLMProviderError
from app.llm.base import LLMMessage
from app.llm.json_utils import extract_json
from app.llm.mock_provider import MockProvider


def test_extract_json_from_fenced_block():
    text = 'Here is the plan:\n```json\n{"a": 1, "b": [1, 2]}\n```\nLet me know if you need changes.'
    result = extract_json(text)
    assert result == {"a": 1, "b": [1, 2]}


def test_extract_json_from_raw_object():
    text = '{"a": 1}'
    assert extract_json(text) == {"a": 1}


def test_extract_json_from_surrounding_prose():
    text = 'Sure, here you go: {"key": "value"} -- hope that helps!'
    assert extract_json(text) == {"key": "value"}


def test_extract_json_raises_for_no_json():
    with pytest.raises(LLMProviderError):
        extract_json("This response has no JSON in it at all.")


@pytest.mark.asyncio
async def test_mock_provider_resolves_by_agent_marker():
    provider = MockProvider()
    messages = [
        LLMMessage(role="system", content="You are the planner. [AGENT:PLANNER]"),
        LLMMessage(role="user", content="Build a todo app"),
    ]
    response = await provider.generate(messages)
    data = extract_json(response.content)
    assert "items" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_mock_provider_health_check():
    provider = MockProvider()
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_mock_provider_stream_yields_chunks():
    provider = MockProvider()
    messages = [LLMMessage(role="system", content="[AGENT:CODER]")]
    chunks = [chunk async for chunk in provider.stream(messages)]
    assert len(chunks) > 1
    assert "".join(chunks).strip().startswith("{")
