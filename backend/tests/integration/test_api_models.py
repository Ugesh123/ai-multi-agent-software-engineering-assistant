from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_models_returns_configured_default(api_client):
    resp = await api_client.get("/api/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "models" in body
    assert "current_default" in body
    # In test mode the provider is "mock", so Ollama's /api/tags won't be
    # queried (or will fail gracefully); either way this must not error.
