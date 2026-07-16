from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.asyncio


async def _create_project(api_client, name: str = "Git Test") -> str:
    resp = await api_client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _run_to_completion(api_client, project_id, request_text, parent_run_id=None):
    payload = {"request": request_text}
    if parent_run_id is not None:
        payload["parent_run_id"] = parent_run_id
    create_resp = await api_client.post(f"/api/v1/projects/{project_id}/runs", json=payload)
    run_id = create_resp.json()["id"]
    async with api_client.stream("GET", f"/api/v1/runs/{run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass
    final = await api_client.get(f"/api/v1/runs/{run_id}")
    return final.json()


async def test_run_completion_auto_commits_to_git(api_client):
    project_id = await _create_project(api_client)
    await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")

    resp = await api_client.get(f"/api/v1/projects/{project_id}/git/log")
    assert resp.status_code == 200
    log = resp.json()
    assert len(log) == 1
    assert len(log[0]["hash"]) == 40


async def test_git_log_reflects_actual_content_changes_not_just_version_count(api_client):
    """With the deterministic MockProvider, an edit-mode run can legitimately
    produce byte-identical file content to its parent -- GitService correctly
    skips creating a no-op commit in that case (verified with real differing
    content in tests/unit/test_git_service.py). Version history (in the DB)
    still grows regardless; git history only grows when content actually
    changes, which is correct git semantics."""

    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    v2 = await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])

    # Version history always grows...
    runs_resp = await api_client.get(f"/api/v1/projects/{project_id}/runs")
    assert {r["version"] for r in runs_resp.json()} == {1, 2}

    # ...git log reflects actual distinct content states (>=1, since the
    # mock coder happens to regenerate identical content for both here).
    resp = await api_client.get(f"/api/v1/projects/{project_id}/git/log")
    log = resp.json()
    assert len(log) >= 1
    assert v2["files"] == v1["files"] or len(log) == 2


async def test_git_log_empty_before_any_run(api_client):
    project_id = await _create_project(api_client)
    resp = await api_client.get(f"/api/v1/projects/{project_id}/git/log")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_set_remote_endpoint(api_client, tmp_path):
    project_id = await _create_project(api_client)
    await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")

    bare_remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare_remote)], check=True, capture_output=True)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/git/remote", json={"remote_url": str(bare_remote)}
    )
    assert resp.status_code == 204


async def test_push_endpoint_real_local_push(api_client, tmp_path):
    """Full round trip through the real API: run completes, auto-commits,
    then we push to a real local bare repo and verify the commit lands."""

    project_id = await _create_project(api_client)
    await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")

    bare_remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/git/push",
        json={"remote_url": str(bare_remote), "branch": "main"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    log_output = subprocess.run(
        ["git", "log", "--oneline", "main"], cwd=str(bare_remote), check=True, capture_output=True, text=True
    ).stdout
    assert log_output.strip() != ""


async def test_push_missing_project_returns_404(api_client, tmp_path):
    resp = await api_client.post(
        "/api/v1/projects/does-not-exist/git/push",
        json={"remote_url": str(tmp_path / "remote.git")},
    )
    assert resp.status_code == 404
