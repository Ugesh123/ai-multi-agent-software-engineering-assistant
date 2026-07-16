# API Reference

Base URL: `http://localhost:8000/api/v1` (configurable via `MACA_API_V1_PREFIX`).

All request/response bodies are JSON unless noted. Errors follow a uniform
shape: `{"error": string, "details": object}` with the HTTP status code
indicating the error class (`404` not found, `409` conflict/invalid state,
`422` validation, `502` upstream LLM failure, `500` unexpected).

## Health

### `GET /health`
Returns backend status and whether the configured LLM provider is reachable.
```json
{ "status": "ok", "llm_provider": "ollama", "llm_healthy": true }
```

## Projects

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects` | Create a project |
| `GET` | `/projects` | List all projects |
| `GET` | `/projects/{id}` | Get one project |
| `PATCH` | `/projects/{id}` | Rename / update description |
| `DELETE` | `/projects/{id}` | Delete a project (cascades to its runs) |

`POST /projects` body: `{"name": string, "description"?: string}` -> `201` with the `Project`.

## Runs (versions)

Every run is a numbered version within its project (v1, v2, ...).

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/{id}/runs` | Create a run (kicks off once streamed) |
| `GET` | `/projects/{id}/runs` | List a project's runs (version history) |
| `POST` | `/projects/{id}/runs/restore` | Instantly restore a prior version as a new one |
| `GET` | `/runs/{id}` | Get current run state (poll-safe) |
| `GET` | `/runs/{id}/stream` | SSE -- executes the run, streaming agent-by-agent progress |
| `GET` | `/runs/{id}/diff` | Diff this run vs. its parent, or `?compare_to={id}` |
| `GET` | `/runs/{id}/download` | Download the run's files as a ZIP |

### `POST /projects/{id}/runs`
```json
{
  "request": "Build a CLI todo app",
  "parent_run_id": null,
  "model": null
}
```
- `parent_run_id` (optional): edit mode -- the Coder agent builds on this prior
  **completed** run's files instead of starting fresh. Must belong to the
  same project and be `completed`, or this returns `409`.
- `model` (optional): per-run override. Bare name (`"llama3"`) swaps the
  model within the configured provider; `"provider:model"` (e.g.
  `"anthropic:claude-sonnet-4-5"`) swaps the provider for just this run.

Returns `201` with the run in `status: "pending"`. Nothing executes until
you open the stream.

### `GET /runs/{id}/stream`
Server-Sent Events. Each `data:` frame:
```json
{
  "run_id": "...",
  "status": "coding",
  "latest_message": { "role": "coder", "content": "...", "id": "...", "created_at": "...", "metadata": {} },
  "review_iterations": 0,
  "test_iterations": 0
}
```
Terminated by `event: done`. The run is persisted after every agent step, so
`GET /runs/{id}` always reflects the latest state even if the stream
connection drops. Calling this on a non-pending run returns `409` (validated
before the stream opens, so it's a proper status code).

### `GET /runs/{id}/diff`
```json
{
  "added": ["app/new_file.py"],
  "deleted": ["app/old_file.py"],
  "modified": [
    { "path": "app/core.py", "unified_diff": "--- a/app/core.py\n+++ b/app/core.py\n...", "added_lines": 3, "removed_lines": 1 }
  ],
  "unchanged": ["README.md"]
}
```

### `POST /projects/{id}/runs/restore`
```json
{ "source_run_id": "..." }
```
Creates a new version whose files/architecture/documentation are an exact
copy of `source_run_id` -- no agents invoked, instant, `status: "completed"`
immediately.

## Reference documents (RAG)

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/{id}/documents` | Upload a .txt/.md/.pdf (multipart) |
| `GET` | `/projects/{id}/documents` | List uploaded documents |
| `DELETE` | `/projects/{id}/documents/{doc_id}` | Delete a document |
| `GET` | `/projects/{id}/search?q=...&top_k=5` | Query the RAG index directly |

Uploads are capped at 10MB and validated against an extension/content-type
allowlist. Search queries both uploaded documents and the project's own
generated code (auto-reindexed after every completed run).

## Models

### `GET /models`
```json
{ "models": [{"name": "qwen3:14b", "provider": "ollama"}], "current_default": "qwen3:14b" }
```
Queries Ollama's `/api/tags` live when the configured provider is Ollama.

## Git

| Method | Path | Description |
|---|---|---|
| `GET` | `/projects/{id}/git/log` | Real `git log` for the project's local repo |
| `POST` | `/projects/{id}/git/remote` | Set the `origin` remote URL |
| `POST` | `/projects/{id}/git/push` | Push to a remote |

Every completed run auto-commits a full working-tree snapshot (no-op commits
are skipped when content is unchanged). `POST /git/push` body:
```json
{ "remote_url": "https://github.com/you/repo.git", "token": "ghp_...", "branch": "main" }
```
`token` is used only for this single push (injected into the URL
transiently) and is never persisted or logged.

## Interactive docs

FastAPI auto-generates OpenAPI docs at `/docs` (Swagger UI) and `/redoc`
while the backend is running.
