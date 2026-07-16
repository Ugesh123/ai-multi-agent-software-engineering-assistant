# Deployment Guide

This is a local, single-user development tool -- see
`ARCHITECTURE.md` (Security model section) before considering any
deployment beyond localhost or a trusted private network.

## Option 1: Docker Compose (recommended for a private server)

See `DOCKER.md`. `docker compose up --build` on any machine with Docker.
For anything beyond a single trusted user's home network, put a reverse
proxy (Caddy, nginx, Traefik) in front with TLS and, at minimum, HTTP basic
auth or an OAuth2 proxy -- the app itself has none.

## Option 2: Bare-metal / VM (systemd)

```ini
# /etc/systemd/system/maca-backend.service
[Unit]
Description=Multi-Agent Coding Assistant backend
After=network.target

[Service]
WorkingDirectory=/opt/maca/backend
Environment=MACA_ENVIRONMENT=production
Environment=MACA_DATABASE_URL=sqlite+aiosqlite:////opt/maca/data/maca.db
ExecStart=/opt/maca/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
User=maca

[Install]
WantedBy=multi-user.target
```
Build the frontend once (`npm run build`) and serve `frontend/dist/` as
static files from nginx/Caddy, proxying `/api/*` to `localhost:8000`
(mirroring `frontend/nginx.conf`).

## Switching to PostgreSQL

SQLite is the default and is fine for single-user local use. For anything
with more concurrent write load:

```bash
pip install asyncpg
```
```
MACA_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/maca
```
No code changes needed -- `app/db/base.py` builds the async engine directly
from the URL. Run `init_models()` (or add Alembic) against the new database
before first use; there's no migration tool wired up yet (see
`LOCAL_DEVELOPMENT.md`, Database migrations section).

## Environment checklist for production

- `MACA_ENVIRONMENT=production`
- `MACA_LLM_PROVIDER` set explicitly (ollama or anthropic)
- `MACA_CORS_ALLOW_ORIGINS` set to your actual frontend origin(s), not left
  at the localhost dev defaults
- `MACA_DATABASE_URL` pointing at a persistent volume or managed database
- `MACA_WORKSPACE_ROOT` on a volume with enough space for sandbox execution
  scratch space and per-project git repos
- If using Anthropic: `MACA_ANTHROPIC_API_KEY` from a secrets manager, never
  committed or baked into an image layer
- A reverse proxy terminating TLS and, if exposed beyond a trusted network,
  providing authentication (the app has none of its own)

## Backups

Everything that matters is under `MACA_WORKSPACE_ROOT` (git repos) and the
SQLite/Postgres database (`MACA_DATABASE_URL`) -- back up both together so
version history in the DB and git history stay consistent.
