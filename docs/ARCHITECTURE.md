# Architecture Overview

## System overview

```mermaid
flowchart LR
    subgraph Client["Browser"]
        UI["React SPA\n(Vite, TS, Zustand, Monaco)"]
    end

    subgraph Server["Backend (FastAPI)"]
        API["REST + SSE routes"]
        WF["WorkflowService"]
        RAG["RagService"]
        GIT["GitService"]
        GRAPH["Compiled LangGraph"]
        DB[("SQLite / Postgres\nvia SQLAlchemy async")]
    end

    subgraph External["Local / hosted"]
        OLLAMA["Ollama\n(chat + embeddings)"]
        ANTHROPIC["Anthropic API\n(optional)"]
        SANDBOX["Sandbox pytest\nsubprocess"]
        REPO["Local git repo\nper project"]
    end

    UI -- "HTTP + SSE" --> API
    API --> WF
    API --> RAG
    API --> GIT
    WF --> GRAPH
    WF --> DB
    RAG --> DB
    GRAPH -- "LLM calls" --> OLLAMA
    GRAPH -- "LLM calls" --> ANTHROPIC
    GRAPH -- "real test execution" --> SANDBOX
    GIT --> REPO
```

## The agent pipeline

Six LangGraph nodes, two capped feedback loops. The Tester node does not ask
an LLM whether tests "would" pass -- it materializes the generated files into
an isolated temp directory and actually runs `pytest`.

```mermaid
stateDiagram-v2
    [*] --> Planner
    Planner --> Architect
    Architect --> Coder
    Coder --> Reviewer
    Reviewer --> Coder: changes requested (iterations < limit)
    Reviewer --> Tester: approved, or iteration cap reached
    Tester --> Coder: tests failed (iterations < limit)
    Tester --> Documentation: tests passed, or iteration cap reached
    Documentation --> [*]
```

| Agent | Responsibility | LLM call? |
|---|---|---|
| Planner | Breaks the request into an ordered task list | Yes |
| Architect | Produces component design, tech choices, file layout | Yes |
| Coder | Generates/edits files -- returns only **changed** files, merged with existing state | Yes |
| Reviewer | Code review against the design; approves or requests changes | Yes |
| Tester | **Actually executes `pytest`** in a sandboxed subprocess | No (static-analysis fallback only for non-Python targets) |
| Documentation | Writes the final README from the real generated files | Yes |

## Request lifecycle (a single run)

```mermaid
sequenceDiagram
    participant U as Browser
    participant API as FastAPI
    participant WF as WorkflowService
    participant RAG as RagService
    participant G as LangGraph
    participant DB as Database

    U->>API: POST /projects/{id}/runs
    API->>WF: create_run()
    WF->>DB: insert AgentRun (status=pending, version=N+1)
    API-->>U: 201 run_id, status=pending

    U->>API: GET /runs/{id}/stream (SSE)
    API->>WF: stream_run_execution()
    WF->>RAG: retrieve(project_id, request)
    RAG-->>WF: relevant chunks (docs + prior code)
    WF->>G: astream(initial_state)
    loop each agent step
        G-->>WF: partial state
        WF->>DB: persist state
        WF-->>U: SSE data - status, latest_message
    end
    WF->>RAG: ingest_generated_files() (re-index)
    WF->>DB: persist commit_message
    Note over WF: GitService.commit_version()
    WF-->>U: event - done
```

## Data model

```mermaid
erDiagram
    PROJECT ||--o{ AGENT_RUN : has
    PROJECT ||--o{ REFERENCE_DOCUMENT : has
    PROJECT ||--o{ DOCUMENT_CHUNK : has
    AGENT_RUN ||--o| AGENT_RUN : "parent_run_id (edit lineage)"

    PROJECT {
        string id PK
        string name
        string description
    }
    AGENT_RUN {
        string id PK
        string project_id FK
        string parent_run_id FK "nullable, self-referential"
        int version
        string status
        string request
        string commit_message
        string model "nullable per-run override"
        json plan
        json architecture
        json files "complete current file set"
        json review
        json test_report
        text documentation
        json messages
    }
    REFERENCE_DOCUMENT {
        string id PK
        string project_id FK
        string filename
        text extracted_text
    }
    DOCUMENT_CHUNK {
        string id PK
        string project_id FK
        string source_type "generated_file or reference_doc"
        string source_id
        text content
        json embedding
    }
```

Note the deliberate choice to store `files`, `plan`, `architecture`, `review`,
`test_report`, and `messages` as JSON columns on the `AGENT_RUN` aggregate
rather than normalizing into a dozen join tables: this aggregate is always
loaded and saved as a whole, never queried piecemeal, so JSON columns avoid
join overhead without sacrificing queryability on the columns that matter
(`status`, `version`, `project_id`, timestamps are real indexed columns).

## Layering (Clean Architecture)

```mermaid
flowchart TD
    A["API layer (FastAPI routes, Pydantic schemas)"] --> B["Service layer (WorkflowService, RagService, GitService, ProjectService)"]
    B --> C["Domain layer (dataclasses: AgentRun, Project, ...)"]
    B --> D["Repository layer (SQLAlchemy repositories)"]
    D --> E["ORM layer (SQLAlchemy models)"]
    B --> F["Agent/Graph layer (LangGraph nodes + compiled StateGraph)"]
    F --> G["Provider layer (LLMProvider, EmbeddingProvider abstractions)"]
```

- **Domain** objects (`app/domain/models.py`) are plain dataclasses with zero
  framework imports -- no FastAPI, no SQLAlchemy, no LangGraph.
- **Repositories** convert between ORM rows and domain objects at the
  persistence boundary (`app/db/mappers.py`); services never see ORM types.
- **Providers** (`LLMProvider`, `EmbeddingProvider`) are the single swap
  point between `Ollama` (default, real), `Anthropic` (real, alternate), and
  `Mock` (deterministic, tests only) -- this is what lets the entire test
  suite run with zero network calls while production code is unchanged.

## Security model

This is a **local, single-user development tool**. Deliberate scope
decisions, stated explicitly:

- **No authentication/authorization.** The FastAPI app has no user accounts,
  sessions, or API keys of its own. It's designed to run on `localhost` for
  one developer. Exposing it beyond localhost without adding an auth layer
  (e.g., a reverse proxy with OAuth2/OIDC in front) is not supported.
- **Path traversal defenses** are applied everywhere generated content
  touches the filesystem: the sandbox test executor, the git commit
  materializer, and the ZIP export all resolve paths and reject anything
  that would escape their target directory (verified by dedicated tests).
- **Upload validation**: reference documents are restricted to an allowlist
  of extensions/content-types (`.txt`, `.md`, `.pdf`) and a 10MB size cap.
- **Git tokens** are accepted per-push-request only, injected into the
  remote URL transiently for that single `git push` subprocess call, and
  never written to disk, the database, or logs (verified by a dedicated
  leak-detection test).
- **Secrets** (`MACA_ANTHROPIC_API_KEY`) come from environment variables
  only and are never logged.
- **CORS** is restricted to an explicit origin allowlist, not `*`.
