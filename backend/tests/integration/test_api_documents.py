from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def _create_project(api_client, name: str = "RAG Test") -> str:
    resp = await api_client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_upload_text_reference_document(api_client):
    project_id = await _create_project(api_client)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("spec.txt", b"The system must support OAuth login.", "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "spec.txt"
    assert body["project_id"] == project_id
    assert "OAuth" in body["preview"]


async def test_list_reference_documents(api_client):
    project_id = await _create_project(api_client)

    await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("a.txt", b"content a", "text/plain")},
    )
    await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("b.txt", b"content b", "text/plain")},
    )

    resp = await api_client.get(f"/api/v1/projects/{project_id}/documents")
    assert resp.status_code == 200
    filenames = {d["filename"] for d in resp.json()}
    assert filenames == {"a.txt", "b.txt"}


async def test_delete_reference_document(api_client):
    project_id = await _create_project(api_client)

    upload = await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("temp.txt", b"temporary content", "text/plain")},
    )
    doc_id = upload.json()["id"]

    resp = await api_client.delete(f"/api/v1/projects/{project_id}/documents/{doc_id}")
    assert resp.status_code == 204

    resp = await api_client.get(f"/api/v1/projects/{project_id}/documents")
    assert resp.json() == []


async def test_upload_empty_document_rejected(api_client):
    project_id = await _create_project(api_client)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("empty.txt", b"   ", "text/plain")},
    )
    assert resp.status_code == 422


async def test_upload_unsupported_file_type_rejected(api_client):
    project_id = await _create_project(api_client)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert resp.status_code == 422


async def test_search_project_context(api_client):
    project_id = await _create_project(api_client)

    await api_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("auth-spec.txt", b"Users must authenticate using OAuth2 tokens.", "text/plain")},
    )

    resp = await api_client.get(f"/api/v1/projects/{project_id}/search", params={"q": "OAuth2 authentication"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert results[0]["source_type"] == "reference_doc"


async def test_search_missing_project_returns_404(api_client):
    resp = await api_client.get("/api/v1/projects/does-not-exist/search", params={"q": "test"})
    assert resp.status_code == 404
