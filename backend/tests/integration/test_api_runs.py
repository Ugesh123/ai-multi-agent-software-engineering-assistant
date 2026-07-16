from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.asyncio


async def _create_project(api_client, name: str = "Stream Test") -> str:
    resp = await api_client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_run_returns_pending(api_client):
    project_id = await _create_project(api_client)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["project_id"] == project_id


async def test_create_run_for_missing_project_returns_404(api_client):
    resp = await api_client.post(
        "/api/v1/projects/does-not-exist/runs", json={"request": "Build something"}
    )
    assert resp.status_code == 404


async def test_create_run_rejects_empty_request(api_client):
    project_id = await _create_project(api_client)
    resp = await api_client.post(f"/api/v1/projects/{project_id}/runs", json={"request": ""})
    assert resp.status_code == 422


async def test_stream_run_executes_full_workflow(api_client):
    project_id = await _create_project(api_client)

    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test."},
    )
    run_id = create_resp.json()["id"]

    events = []
    async with api_client.stream("GET", f"/api/v1/runs/{run_id}/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                payload = line[len("data: ") :]
                if payload.strip():
                    parsed = json.loads(payload)
                    if parsed:  # skip the empty {} "done" sentinel frame
                        events.append(parsed)

    # One event per completed agent step (planner..documentation), the last
    # of which reflects the fully completed run.
    assert len(events) >= 6
    assert events[-1]["status"] == "completed"

    # GET /runs/{id} reflects the same fully persisted final state.
    get_resp = await api_client.get(f"/api/v1/runs/{run_id}")
    assert get_resp.status_code == 200
    run = get_resp.json()
    assert run["status"] == "completed"
    assert len(run["files"]) == 2
    assert run["test_report"]["verdict"] == "passed"
    assert run["review"]["verdict"] == "approved"
    assert "Generated Project" in run["documentation"]


async def test_stream_run_twice_returns_conflict(api_client):
    project_id = await _create_project(api_client)
    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test."},
    )
    run_id = create_resp.json()["id"]

    async with api_client.stream("GET", f"/api/v1/runs/{run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass

    resp = await api_client.get(f"/api/v1/runs/{run_id}/stream")
    assert resp.status_code == 409


async def test_get_missing_run_returns_404(api_client):
    resp = await api_client.get("/api/v1/runs/does-not-exist")
    assert resp.status_code == 404


async def test_list_project_runs(api_client):
    project_id = await _create_project(api_client)
    await api_client.post(
        f"/api/v1/projects/{project_id}/runs", json={"request": "Build a function"}
    )
    await api_client.post(
        f"/api/v1/projects/{project_id}/runs", json={"request": "Build another function"}
    )

    resp = await api_client.get(f"/api/v1/projects/{project_id}/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_download_run_zip_after_completion(api_client):
    import io
    import zipfile

    project_id = await _create_project(api_client)
    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test."},
    )
    run_id = create_resp.json()["id"]

    async with api_client.stream("GET", f"/api/v1/runs/{run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass

    resp = await api_client.get(f"/api/v1/runs/{run_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = archive.namelist()
        assert "app/core.py" in names
        assert "README.md" in names


async def test_download_run_zip_before_files_generated_fails(api_client):
    project_id = await _create_project(api_client)
    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function"},
    )
    run_id = create_resp.json()["id"]

    resp = await api_client.get(f"/api/v1/runs/{run_id}/download")
    assert resp.status_code == 409


async def test_edit_mode_run_against_completed_parent_succeeds(api_client):
    project_id = await _create_project(api_client)

    first = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test."},
    )
    first_run_id = first.json()["id"]

    async with api_client.stream("GET", f"/api/v1/runs/{first_run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass

    second = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Add a helper function", "parent_run_id": first_run_id},
    )
    assert second.status_code == 201
    assert second.json()["parent_run_id"] == first_run_id

    second_run_id = second.json()["id"]
    async with api_client.stream("GET", f"/api/v1/runs/{second_run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass

    final = await api_client.get(f"/api/v1/runs/{second_run_id}")
    final_body = final.json()
    paths = {f["path"] for f in final_body["files"]}
    # The edit-mode run's file set must still include the original files.
    assert "app/core.py" in paths
    assert "tests/test_core.py" in paths


async def test_edit_mode_run_against_pending_parent_fails(api_client):
    project_id = await _create_project(api_client)

    first = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function"},
    )
    first_run_id = first.json()["id"]  # never streamed -> stays "pending"

    second = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Add a helper", "parent_run_id": first_run_id},
    )
    assert second.status_code == 409


async def test_edit_mode_run_against_missing_parent_fails(api_client):
    project_id = await _create_project(api_client)

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Add a helper", "parent_run_id": "does-not-exist"},
    )
    assert resp.status_code == 404


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


async def test_version_numbers_increment_sequentially(api_client):
    project_id = await _create_project(api_client)

    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    assert v1["version"] == 1

    v2 = await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])
    assert v2["version"] == 2
    assert v2["parent_run_id"] == v1["id"]


async def test_completed_run_has_generated_commit_message(api_client):
    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    assert v1["commit_message"]
    assert "added" in v1["commit_message"]


async def test_diff_endpoint_against_parent(api_client):
    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    v2 = await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])

    resp = await api_client.get(f"/api/v1/runs/{v2['id']}/diff")
    assert resp.status_code == 200
    diff = resp.json()
    # v2 is seeded from v1's files and the mock coder always emits the same
    # two files again as "creates" merged over the seeded set -- so v1's
    # files should show up as unchanged (or modified, never lost) rather
    # than appearing deleted.
    assert "app/core.py" not in diff["deleted"]
    assert "tests/test_core.py" not in diff["deleted"]


async def test_diff_endpoint_explicit_compare_to(api_client):
    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    v2 = await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])

    resp = await api_client.get(f"/api/v1/runs/{v2['id']}/diff", params={"compare_to": v1["id"]})
    assert resp.status_code == 200


async def test_diff_across_projects_rejected(api_client):
    project_a = await _create_project(api_client, )
    project_b_resp = await api_client.post("/api/v1/projects", json={"name": "Project B"})
    project_b = project_b_resp.json()["id"]

    run_a = await _run_to_completion(api_client, project_a, "Build a function that doubles a number, with a test.")
    run_b = await _run_to_completion(api_client, project_b, "Build a function that doubles a number, with a test.")

    resp = await api_client.get(f"/api/v1/runs/{run_a['id']}/diff", params={"compare_to": run_b["id"]})
    assert resp.status_code == 409


async def test_restore_version_creates_new_completed_run_instantly(api_client):
    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    # v2 exists only to prove restoring v1 correctly becomes v3 (sequential
    # numbering) even with an intervening version -- not asserted on directly.
    _v2 = await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs/restore", json={"source_run_id": v1["id"]}
    )
    assert resp.status_code == 201
    restored = resp.json()
    assert restored["status"] == "completed"
    assert restored["version"] == 3
    assert restored["parent_run_id"] == v1["id"]
    assert {f["path"] for f in restored["files"]} == {f["path"] for f in v1["files"]}
    assert "Restored to v1" in restored["commit_message"]

    # sanity: v2 untouched, still present in history
    resp = await api_client.get(f"/api/v1/projects/{project_id}/runs")
    versions = {r["version"] for r in resp.json()}
    assert versions == {1, 2, 3}


async def test_restore_from_pending_run_fails(api_client):
    project_id = await _create_project(api_client)
    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs", json={"request": "Build a function"}
    )
    pending_id = create_resp.json()["id"]

    resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs/restore", json={"source_run_id": pending_id}
    )
    assert resp.status_code == 409


async def test_download_zip_for_any_prior_version(api_client):
    project_id = await _create_project(api_client)
    v1 = await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")
    await _run_to_completion(api_client, project_id, "Add a helper", parent_run_id=v1["id"])

    # v1's zip must still be downloadable even after v2 exists.
    resp = await api_client.get(f"/api/v1/runs/{v1['id']}/download")
    assert resp.status_code == 200


async def test_run_with_explicit_mock_model_override_executes_successfully(api_client):
    """Per-run model override: 'mock:anything' should build a fresh graph
    bound to a MockProvider for just this run, regardless of container
    default, and persist the model spec on the run record."""

    project_id = await _create_project(api_client)
    create_resp = await api_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"request": "Build a function that doubles a number, with a test.", "model": "mock:test-model"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["model"] == "mock:test-model"

    run_id = create_resp.json()["id"]
    async with api_client.stream("GET", f"/api/v1/runs/{run_id}/stream") as resp:
        async for _ in resp.aiter_lines():
            pass

    final = await api_client.get(f"/api/v1/runs/{run_id}")
    assert final.json()["status"] == "completed"


async def test_completed_run_auto_indexes_generated_files_for_rag(api_client):
    """After a run completes, its generated files should be searchable via
    the RAG endpoint -- confirming automatic re-indexing actually happened,
    not just that the code path didn't crash."""

    project_id = await _create_project(api_client)
    await _run_to_completion(api_client, project_id, "Build a function that doubles a number, with a test.")

    resp = await api_client.get(f"/api/v1/projects/{project_id}/search", params={"q": "double the given value"})
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["source_type"] == "generated_file" for r in results)
