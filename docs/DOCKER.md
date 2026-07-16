# Docker Guide

## Quick start

```bash
docker compose up --build
```

This builds and starts three services:

| Service | Port | Description |
|---|---|---|
| ollama | 11434 | Local LLM inference + embeddings |
| backend | 8000 | FastAPI app |
| frontend | 80 | Static build served via nginx, proxying /api to backend |

Open `http://localhost`. First boot: pull a model into the Ollama container
before running anything:

```bash
docker compose exec ollama ollama pull qwen3:14b
docker compose exec ollama ollama pull nomic-embed-text
```

## Images

`backend/Dockerfile` -- multi-stage:
1. `builder`: installs Python dependencies into a venv (`pip install -r requirements.txt`).
2. `runtime`: slim `python:3.12-slim` + `git` (required at runtime by
   `GitService`'s real `git` CLI calls) + the venv + app code, running as a
   non-root user. Exposes 8000, with a HEALTHCHECK against `/api/v1/health`.

`frontend/Dockerfile` -- multi-stage:
1. `builder`: `node:22-slim`, `npm ci && npm run build`.
2. `runtime`: `nginx:1.27-alpine` serving the static build, reverse-proxying
   `/api/*` to the `backend` service (see `frontend/nginx.conf` -- note
   `proxy_buffering off` for the SSE run-stream endpoint to flush
   immediately rather than buffering).

## Configuration

All backend settings are environment variables (prefix MACA_), set in
`docker-compose.yml`'s `backend.environment` block. Override at run time:

```bash
MACA_OLLAMA_MODEL=llama3:8b docker compose up --build
```

Persistent data (`data/maca.db`, per-project git repos, sandbox workspaces)
lives in named volumes (`backend_data`, `backend_workspaces`) so it survives
`docker compose down` (but not `docker compose down -v`).

## GPU acceleration

If the host has an NVIDIA GPU and the NVIDIA Container Toolkit installed,
uncomment the `deploy.resources.reservations.devices` block under the
`ollama` service in `docker-compose.yml`.

## Building images individually

```bash
docker build -t maca-backend ./backend
docker build -t maca-frontend ./frontend
```

## Running the backend test suite inside the built image

```bash
docker build -t maca-backend ./backend
docker run --rm -e MACA_LLM_PROVIDER=mock -e MACA_EMBEDDING_PROVIDER=mock \
  --entrypoint python3 maca-backend -m pytest -q
```
(Requires `pytest` to be present in the image; the production Dockerfile
installs `requirements.txt`, which includes it -- for a leaner production
image, split into `requirements.txt` + `requirements-dev.txt` and adjust
the builder stage.)

## Verifying without Docker installed

If Docker isn't available in your environment, you can still verify the
exact commands the images run will succeed by mirroring them locally:

```bash
# Mirrors the backend image's dependency install
python3 -m venv /tmp/verify-venv && /tmp/verify-venv/bin/pip install -r backend/requirements.txt

# Mirrors the frontend image's build
cd frontend && npm ci && npm run build
```
