# Multi-Agent Coding Assistant

A local, multi-agent AI software engineer. Describe a feature; six specialized
LangGraph agents — **Planner, Architect, Coder, Reviewer, Tester, Documentation**
— plan it, design it, implement it, review it, actually run its tests in a
sandbox, and document it. Runs entirely on your machine against a local
[Ollama](https://ollama.com) model by default.

Think Cursor / Claude Code, but with a visible, inspectable multi-agent
pipeline instead of a single black-box model call.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.12-blue)
![node](https://img.shields.io/badge/node-22-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Capabilities

- **Six-agent LangGraph pipeline** with real feedback loops: the Reviewer can
  send code back to the Coder; the Tester actually executes `pytest` in an
  isolated sandbox (not an LLM guess) and can send failures back too — both
  loops are iteration-capped.
- **Live streaming** of every agent step over Server-Sent Events, rendered as
  a real-time pipeline visualization.
- **Version history** — every run is a numbered version (v1, v2, v3, ...).
  Edit any prior version incrementally, restore any version instantly,
  compare any two versions side-by-side with a Monaco diff viewer, and
  download any version as a ZIP.
- **Automatic git history** — every completed version is committed to a real
  local git repository with a generated commit message; push to GitHub (or
  any remote) with a token, used only for that push and never stored.
- **RAG** over both your own uploaded reference documents (`.txt`/`.md`/`.pdf`)
  and the project's own generated code, grounding the Planner and Architect
  in real context.
- **Multi-model** — swap models per run (`llama3`, `codellama`, ...) or
  switch provider entirely (`anthropic:claude-sonnet-4-5`) without touching
  config.
- **Full IDE-style UI** — VS Code-style file explorer, Monaco editor, dark/light
  theme, responsive layout.

## Quick start

```bash
# 1. Start Ollama and pull a model
ollama pull qwen3:14b
ollama serve

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. See [`docs/INSTALLATION.md`](docs/INSTALLATION.md)
for full prerequisites and [`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md)
for the day-to-day dev workflow.

Prefer containers? See [`docs/DOCKER.md`](docs/DOCKER.md) — one
`docker compose up` boots Ollama, the backend, and the frontend together.

## Documentation

| Doc | Covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, agent pipeline, data model, diagrams |
| [`docs/API.md`](docs/API.md) | Full REST + SSE API reference |
| [`docs/INSTALLATION.md`](docs/INSTALLATION.md) | Prerequisites and first-time setup |
| [`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md) | Running tests, dev workflow, conventions |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production deployment options |
| [`docs/DOCKER.md`](docs/DOCKER.md) | Container build/run reference |
| [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) | Directory-by-directory guide |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Common issues and fixes |

## Tech stack

**Backend:** Python, FastAPI, LangGraph, LangChain, SQLAlchemy (async), SQLite
(Postgres-ready), Ollama / Anthropic providers.
**Frontend:** React, TypeScript, Vite, TailwindCSS v4, Monaco Editor, Zustand.
**Testing:** pytest (142 backend tests), Vitest + Testing Library (frontend).

## Engineering practices

Clean Architecture layering (domain → repository → service → API), dependency
injection via a process-lifetime container, provider abstractions for LLM and
embedding backends (so `MockProvider` drives the entire test suite with zero
network calls), full SOLID/typed Python and TypeScript, and defense-in-depth
security (path-traversal guards on sandbox execution, git operations, and ZIP
export; upload type allowlisting; git tokens never persisted or logged).

## Status and known limitations

This is a local, single-user development tool with **no authentication** —
appropriate for its intended use (running on your own machine), documented
explicitly rather than papered over. See
[`docs/ARCHITECTURE.md#security-model`](docs/ARCHITECTURE.md#security-model)
for the full reasoning and what would need to change for multi-user
deployment.

## 🚧 Project Status

This project is under active development.

- ✅ Multi-agent workflow implemented
- ✅ Backend and frontend completed
- ✅ Local development supported
- 🔄 Deployment improvements are in progress

## License

MIT
