# Project Structure

```
multi-agent-coding-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, lifespan, router registration
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings, env prefix MACA_)
│   │   │   ├── container.py     # DI container: engine, providers, compiled graph, services
│   │   │   ├── exceptions.py    # Domain exception hierarchy -> HTTP status mapping
│   │   │   └── logging.py       # Structured logging setup
│   │   ├── domain/
│   │   │   ├── models.py        # Framework-agnostic dataclasses (AgentRun, Project, ...)
│   │   │   └── enums.py         # RunStatus, AgentRole, ReviewVerdict, ...
│   │   ├── db/
│   │   │   ├── base.py          # Async engine/session factory
│   │   │   ├── models.py        # SQLAlchemy ORM models
│   │   │   ├── mappers.py       # ORM to domain dataclass conversion
│   │   │   ├── repository.py    # ProjectRepository, AgentRunRepository
│   │   │   └── vector_store_repository.py  # RAG chunk storage + cosine search
│   │   ├── llm/
│   │   │   ├── base.py          # LLMProvider abstraction
│   │   │   ├── ollama_provider.py, anthropic_provider.py, mock_provider.py
│   │   │   ├── factory.py       # Provider construction, incl. per-run model resolution
│   │   │   └── json_utils.py    # Robust JSON extraction from LLM text output
│   │   ├── rag/
│   │   │   ├── base.py          # EmbeddingProvider abstraction
│   │   │   ├── ollama_embedding_provider.py, mock_embedding_provider.py
│   │   │   ├── chunking.py      # Text chunker
│   │   │   └── factory.py
│   │   ├── agents/
│   │   │   ├── base.py          # BaseAgent template (LLM call, retry, transcript)
│   │   │   ├── state.py         # LangGraph WorkflowState TypedDict
│   │   │   └── planner.py, architect.py, coder.py, reviewer.py, tester.py, documentation.py
│   │   ├── graph/
│   │   │   ├── workflow.py      # StateGraph wiring + conditional feedback-loop edges
│   │   │   └── factory.py       # Assembles agents + sandbox into a compiled graph
│   │   ├── services/
│   │   │   ├── workflow_service.py       # Run lifecycle, streaming, RAG/git sync
│   │   │   ├── project_service.py
│   │   │   ├── rag_service.py            # Document ingestion + retrieval
│   │   │   ├── git_service.py            # Real git CLI wrapping
│   │   │   ├── diff_service.py           # Version diffing, commit message generation
│   │   │   ├── project_export_service.py # ZIP export
│   │   │   └── sandbox_executor.py       # Real pytest execution in an isolated dir
│   │   └── api/
│   │       ├── deps.py, error_handlers.py, schemas.py
│   │       └── routes/
│   │           ├── projects.py, runs.py, documents.py, models.py, git.py, health.py
│   ├── tests/
│   │   ├── unit/            # Fast, isolated (repository, agents, services, providers)
│   │   └── integration/     # Full ASGI app + real SQLite + MockProvider
│   ├── Dockerfile, .dockerignore, requirements.txt, pytest.ini, .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/              # client.ts (fetch wrapper + SSE reader), types.ts
│   │   ├── store/             # useAppStore.ts -- single Zustand store
│   │   ├── lib/                # pipeline.ts, fileTree.ts (pure logic, unit-tested)
│   │   ├── components/
│   │   │   ├── layout/         # TopBar, WorkspaceSidebar
│   │   │   ├── pipeline/       # PipelineRail (signature live-status visualization)
│   │   │   ├── files/          # FileExplorer (VS Code-style tree), CodeEditor (Monaco)
│   │   │   ├── panels/         # Plan/Review/Tests/Docs/Diff/Knowledge/Git/Activity panels
│   │   │   └── RunInput.tsx, ModelSelector.tsx
│   │   ├── pages/               # Dashboard.tsx, Workspace.tsx
│   │   └── test/                # Vitest setup
│   ├── Dockerfile, nginx.conf, .dockerignore, vite.config.ts
│
├── docker-compose.yml         # ollama + backend + frontend
├── docs/                      # This documentation set
└── README.md
```

## Where to look for X

| I want to... | Look at |
|---|---|
| Change an agent's prompt | backend/app/agents/{agent_name}.py |
| Change the pipeline's flow/loops | backend/app/graph/workflow.py |
| Add an API endpoint | backend/app/api/routes/, app/api/schemas.py |
| Change how runs are persisted | backend/app/services/workflow_service.py, app/db/mappers.py |
| Add a new LLM provider | backend/app/llm/ (implement LLMProvider, wire into factory.py) |
| Change the file explorer / editor | frontend/src/components/files/ |
| Change the pipeline visualization | frontend/src/components/pipeline/PipelineRail.tsx, src/lib/pipeline.ts |
| Change global app state | frontend/src/store/useAppStore.ts |
| Change the theme/design tokens | frontend/src/index.css (the @theme block) |
