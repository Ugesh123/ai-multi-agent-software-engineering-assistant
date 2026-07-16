from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(api_client):
    resp = await api_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "mock"
    assert body["llm_healthy"] is True


async def test_create_and_get_project(api_client):
    resp = await api_client.post(
        "/api/v1/projects", json={"name": "Todo App", "description": "A CLI todo app"}
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Todo App"

    resp = await api_client.get(f"/api/v1/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_missing_project_returns_404(api_client):
    resp = await api_client.get("/api/v1/projects/does-not-exist")
    assert resp.status_code == 404
    assert "error" in resp.json()


async def test_list_projects(api_client):
    await api_client.post("/api/v1/projects", json={"name": "A"})
    await api_client.post("/api/v1/projects", json={"name": "B"})

    resp = await api_client.get("/api/v1/projects")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert {"A", "B"}.issubset(names)


async def test_create_project_rejects_empty_name(api_client):
    resp = await api_client.post("/api/v1/projects", json={"name": ""})
    assert resp.status_code == 422


async def test_delete_project(api_client):
    resp = await api_client.post("/api/v1/projects", json={"name": "Delete Me"})
    project_id = resp.json()["id"]

    resp = await api_client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 204

    resp = await api_client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404


async def test_rename_project(api_client):
    resp = await api_client.post("/api/v1/projects", json={"name": "Old Name"})
    project_id = resp.json()["id"]

    resp = await api_client.patch(f"/api/v1/projects/{project_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"

    resp = await api_client.get(f"/api/v1/projects/{project_id}")
    assert resp.json()["name"] == "New Name"


async def test_rename_project_missing_returns_404(api_client):
    resp = await api_client.patch("/api/v1/projects/does-not-exist", json={"name": "X"})
    assert resp.status_code == 404
