# Troubleshooting

## llm_healthy: false from GET /api/v1/health

Ollama isn't reachable at MACA_OLLAMA_BASE_URL (default
http://localhost:11434).
- Confirm `ollama serve` is running: `curl http://localhost:11434/api/tags`
- If running in Docker, the backend must use `http://ollama:11434` (the
  service name), not `localhost` -- already set correctly in
  `docker-compose.yml`; only relevant if you've customized it.

## A run gets stuck / never progresses past "planning"

The Planner (or any agent) couldn't produce parseable JSON after
MACA_LLM_MAX_RETRIES attempts, and the SSE stream ended with an error
event. Check the backend logs for AgentExecutionError -- smaller/older
models sometimes wrap JSON in extra prose despite the system prompt.
Try a larger model, or lower MACA_LLM_TEMPERATURE (default 0.2) for
more consistent formatting.

## Backend log shows "ValueError: second argument (exceptions) must be a non-empty sequence" and the run appears stuck (Windows)

This is a known httpx/httpcore/anyio issue, most common on Windows. Root
cause: `MACA_OLLAMA_BASE_URL` pointing at the hostname `localhost`, which
resolves to *both* 127.0.0.1 and ::1 on Windows. httpx's parallel
dual-stack ("happy eyeballs") connection attempt can hit a cancellation
race that raises this exact ValueError -- CPython's own
`ExceptionGroup`/`BaseExceptionGroup` constructor message when given zero
exceptions -- deep inside anyio's connection internals, instead of a clean
connection error.

Fixed as of this version: `MACA_OLLAMA_BASE_URL` now defaults to
`http://127.0.0.1:11434` (an unambiguous single address, avoiding the
dual-stack lookup entirely), and `app/llm/ollama_provider.py`'s retry loop
no longer catches bare `ValueError` -- only `json.JSONDecodeError`
specifically -- so if this class of bug recurs for any other reason, it
surfaces immediately with its real traceback instead of being silently
retried 3x (and then 2x again at the agent level) while looking "stuck"
for minutes at a time.

If you still see this after updating: check your own `backend/.env` for a
leftover `MACA_OLLAMA_BASE_URL=http://localhost:11434` override and change
it to `http://127.0.0.1:11434`.

## Tests always report "no tests ran" even though the Coder generated tests

This was a real bug found and fixed during development (see
app/services/sandbox_executor.py): if MACA_WORKSPACE_ROOT resolves to a
path inside this backend's own project tree, pytest's config
auto-discovery could walk upward and pick up the backend's own
pytest.ini, shadowing the sandboxed project's app package with the real
one. Fixed by (a) always resolving workspace_root to an absolute path and
(b) placing an empty pytest.ini directly in each sandbox directory so
pytest's upward config search stops there. If you see this symptom again,
check that MACA_WORKSPACE_ROOT isn't nested under a directory containing
an unrelated pytest.ini/pyproject.toml/tox.ini.

## git push fails

- "failed to push some refs" / non-fast-forward: the remote has commits
  this repo doesn't. This app always pushes HEAD:branch, not --force --
  resolve manually with a normal git pull/merge in the project's repo
  directory (<workspace_root>/repos/<project_id>) if needed.
- Authentication failed: for GitHub, `token` must be a Personal Access
  Token with repo scope, not your account password. The token is used
  once, transiently, and never stored -- you'll need to re-supply it for
  every push from the UI.
- "repository not found": verify remote_url is exactly right and, for
  a private repo, that the token has access to it.

## SSE stream disconnects with no events / stalls in the browser

Check for an intermediate proxy buffering the response. The provided
nginx.conf already disables buffering (proxy_buffering off) for /api/;
if you've added another proxy layer (e.g. an additional load balancer),
ensure it doesn't buffer chunked/streaming responses either.

## pip install -r requirements.txt fails on an unrelated package

Confirm you're on Python 3.12+; some pinned versions (e.g. pydantic-core)
ship prebuilt wheels only for recent CPython versions and will attempt a
slow/failing source build on older Pythons.

## Frontend shows blank page / console errors about /api/v1/... 404s

In dev, this almost always means the backend isn't running on port 8000 (the
Vite proxy target is hardcoded there in vite.config.ts) -- start it first,
or change the proxy target if you've moved the backend to another port.

## Reference document upload returns 422

Only .txt, .md, and .pdf (10MB max) are accepted. Other file types are
rejected before any parsing is attempted -- see
app/services/rag_service.py's _validate_upload_type.

## docker compose up -- Ollama container has no models

Models aren't baked into the ollama/ollama image. Pull them into the
running container once:
```bash
docker compose exec ollama ollama pull qwen3:14b
docker compose exec ollama ollama pull nomic-embed-text
```
