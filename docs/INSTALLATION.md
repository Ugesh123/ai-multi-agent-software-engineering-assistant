# Installation Guide

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.12+ | Backend |
| Node.js | 22+ | Frontend |
| Ollama (ollama.com) | latest | Local LLM inference (default provider) |
| git | any recent | Version history / commit-per-version |

Optional: Docker + Docker Compose (see `DOCKER.md`) if you'd rather not
install Python/Node locally.

## 1. Install and start Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default chat model and the embedding model (for RAG)
ollama pull qwen3:14b
ollama pull nomic-embed-text

ollama serve   # keep this running
```

Any Ollama-compatible model works -- `qwen3:14b` is the default, configurable
via `MACA_OLLAMA_MODEL`.

## 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # adjust if needed -- defaults work out of the box
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/api/v1/health` should return
`{"status":"ok","llm_provider":"ollama","llm_healthy":true}`. If
`llm_healthy` is `false`, Ollama isn't reachable -- see `TROUBLESHOOTING.md`.

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to
`http://localhost:8000` automatically (see `frontend/vite.config.ts`).

## 4. Optional: Anthropic as an alternate provider

```bash
# in backend/.env
MACA_ANTHROPIC_API_KEY=sk-ant-...
MACA_ANTHROPIC_MODEL=claude-sonnet-4-5   # check docs.claude.com for current names
```
Switch the default provider with `MACA_LLM_PROVIDER=anthropic`, or leave the
default as Ollama and use a per-run override (`"model": "anthropic:claude-sonnet-4-5"`
in the run-creation request) to use it selectively.

## Next steps

- `LOCAL_DEVELOPMENT.md` -- running tests, dev workflow
- `DEPLOYMENT.md` -- production deployment
- `TROUBLESHOOTING.md` -- common setup issues
