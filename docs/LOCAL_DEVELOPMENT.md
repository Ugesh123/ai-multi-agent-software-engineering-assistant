# Local Development Guide

## Running the test suites

```bash
# Backend (142 tests) -- entirely offline, uses MockProvider, no Ollama needed
cd backend
python3 -m pytest -q

# Frontend (23 tests)
cd frontend
npm run test

# Lint
npm run lint          # oxlint, 0 warnings/errors
npx tsc --noEmit       # type check
```

Backend tests never hit a real network or a real Ollama server: `MockProvider`
and `MockEmbeddingProvider` (deterministic, keyed by an `[AGENT:ROLE]`
marker in each agent's system prompt) drive the entire LangGraph pipeline
end-to-end, including a real sandboxed `pytest` execution and a real local
git push to a temporary bare repo -- so the suite is both fast and genuinely
verifies behavior, not just that code doesn't crash.

## Running against mock mode manually

```bash
cd backend
MACA_LLM_PROVIDER=mock MACA_EMBEDDING_PROVIDER=mock \
  MACA_DATABASE_URL="sqlite+aiosqlite:///./dev-mock.db" \
  uvicorn app.main:app --reload --port 8000
```
Useful for frontend development without needing Ollama running.

## Project conventions

- Domain objects never import framework code. `app/domain/models.py` has
  zero FastAPI/SQLAlchemy/LangGraph imports. If you find yourself importing
  one there, the logic belongs in a service instead.
- Services own their session lifecycle. `WorkflowService` and `RagService`
  open short-lived sessions per operation (`session_scope`) rather than
  taking one long-lived session, since they span multiple LangGraph steps
  within a single streaming response.
- New LLM-calling agents extend `BaseAgent` (`app/agents/base.py`),
  implement `system_prompt()`, `build_user_prompt()`, `parse_response()`,
  and embed an `[AGENT:ROLE]` marker in the system prompt so `MockProvider`
  can key a canned response to them for tests.
- Anything touching the filesystem from generated content (sandbox
  execution, git commits, ZIP export) must resolve paths and reject
  anything escaping the target directory -- see the existing
  `_is_safe_archive_path` / path-traversal checks as the pattern to follow.
- Frontend state lives in one Zustand store (`src/store/useAppStore.ts`).
  Components read via selectors (`useAppStore((s) => s.foo)`), never the
  whole store, to avoid unnecessary re-renders.

## Adding a new backend route

1. Add/extend a Pydantic schema in `app/api/schemas.py`.
2. Add the service method (in the relevant `app/services/*.py`).
3. Add the route in `app/api/routes/*.py`, using `Depends()` for services.
4. Register the router in `app/main.py` if it's a new file.
5. Write both a unit test (service logic) and an integration test (through
   the real ASGI app via `tests/integration/conftest.py`'s `api_client`
   fixture) -- the project consistently pairs both.

## Database migrations

There is no migration tool wired up (Alembic) -- `init_models()` calls
`Base.metadata.create_all()` at startup, which is additive-only and fine for
SQLite in local development. If you add a column, either delete the local
`data/maca.db` in dev, or add an Alembic migration before shipping this to a
persistent production database.

## Regenerating the frontend's API types

`frontend/src/api/types.ts` is hand-maintained to mirror
`backend/app/api/schemas.py`. There's no codegen step; when you change a
Pydantic response model, update the matching TypeScript interface in the
same PR.
