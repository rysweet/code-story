# CodeStory Design Specification

## 1. High-Level Architecture

```mermaid
flowchart TD
    CLI[CLI/TUI] -->|Ingest, Query, Config| Service[CodeStory Service]
    Service -->|Ingestion Pipeline| Pipeline[Ingestion Pipeline]
    Pipeline -->|Blarify| Blarify[Blarify (Linux Container)]
    Pipeline -->|FileSystem| FileSystem[FileSystem Step]
    Pipeline -->|Summarizer| Summarizer[Summarizer Step]
    Pipeline -->|Doc Grapher| DocGrapher[Documentation Grapher]
    Service -->|Graph API| GraphDB[Neo4j 5.x (Container)]
    Service -->|AI Client| AI[Azure OpenAI Client]
    Service -->|MCP Adapter| MCP[MCP Adapter (gRPC/HTTP)]
    GraphDB -->|Semantic Search| MCP
    GraphDB -->|Cypher, Vector| Service
    Service -->|Prometheus| Metrics[Metrics/Monitoring]
```

## 2. Major Modules/Packages & Public APIs

| Module/Package         | Public API/Entrypoints                | Responsibility Boundary |
|------------------------|---------------------------------------|------------------------|
| `codestory.cli`        | `main()`, `ingest()`, `query()`, `config()` | CLI/TUI commands, user interaction, help/error |
| `codestory.service`    | `start()`, `stop()`, `status()`, `run_pipeline()` | Service orchestration, job mgmt, config reload |
| `codestory.pipeline`   | `run()`, `cancel()`, `progress()`     | Ingestion pipeline, step orchestration, progress |
| `codestory.blarify`    | `parse()`, `incremental_update()`     | AST/symbol parsing via Blarify, Linux container mgmt |
| `codestory.fs`         | `traverse()`, `apply_ignores()`, `link_ast()` | Filesystem traversal, node creation, linking |
| `codestory.summarizer` | `summarize_node()`, `summarize_repo()`| NL summarization, DAG processing, parallelism |
| `codestory.docgraph`   | `parse_docs()`, `link_entities()`     | Documentation parsing, entity extraction, linking |
| `codestory.graph`      | `query()`, `async_query()`, `init_schema()`, `vector_search()` | Neo4j connection, schema, sync/async, pooling |
| `codestory.ai`         | `complete()`, `embed()`, `chat()`     | Azure OpenAI access, retry/backoff, model selection |
| `codestory.config`     | `load()`, `save()`, `reload()`, `get()` | Typed config, env precedence, KeyVault, hot-reload |
| `codestory.mcp`        | `searchGraph()`, `summarizeNode()`, `pathTo()`, `similarCode()` | MCP server, auth, gRPC/HTTP, rate limits, metrics |

## 3. Technology Choices

- **Language:** Python 3.11+ (strict type checking with pyright)
- **Environment:** All Python via `uv` (env, install, run)
- **Linting:** ruff
- **Testing:** pytest, self-contained, TDD, fixtures
- **Graph DB:** Neo4j 5.x (containerized, local dev, vector search, apoc)
- **AI:** Azure OpenAI (completions, embeddings, chat)
- **CLI/TUI:** Rich (for CLI), textual (optional for TUI)
- **Containerization:** Docker, Linux containers for Blarify and Neo4j
- **Concurrency:** Asyncio for pipeline, thread/process pool for parallel steps
- **Config:** Pydantic, .env, .codestory.toml, Azure KeyVault
- **Metrics:** Prometheus
- **MCP:** gRPC and HTTP, Microsoft Entra ID auth

## 4. Mapping Product Requirements to Components

| Requirement Area         | Component/Module(s)         |
|-------------------------|-----------------------------|
| CLI                     | `codestory.cli`, `codestory.service`, `codestory.config` |
| Ingestion Pipeline      | `codestory.pipeline`, `codestory.blarify`, `codestory.fs`, `codestory.summarizer`, `codestory.docgraph` |
| Blarify Integration     | `codestory.blarify`         |
| FileSystem Step         | `codestory.fs`              |
| Summarizer Step         | `codestory.summarizer`      |
| Documentation Grapher   | `codestory.docgraph`        |
| Graph DB Service        | `codestory.graph`           |
| AI Client               | `codestory.ai`              |
| Configuration           | `codestory.config`          |
| MCP Adapter             | `codestory.mcp`             |
| Infrastructure/Testing  | All modules (test/infra)    |
| Documentation           | All modules (docstrings, guides) |

## 5. Ingestion Pipeline & Blarify Integration

- **Pipeline Steps:** Blarify (AST), FileSystem, Summarizer, Documentation Grapher
- **Extensibility:** Each step is a pluggable module, supports incremental/idempotent runs, progress/cancellation
- **Blarify:** Runs in a Linux container (required for Mac/Windows hosts), invoked via Docker API, outputs AST/symbols
- **Concurrency:** Steps can run in parallel (configurable concurrency), DAG for summarizer
- **Data Flow:** Each step updates the graph DB, links nodes, and emits progress
- **Error Handling:** Graceful cancellation, error reporting, retry logic

## 6. Testing Strategy

- **Self-contained:** All tests manage their own dependencies (no external state)
- **Fixtures:** Shared fixtures for Neo4j (containerized), Blarify, config
- **No hardcoded secrets:** All secrets via env vars, skip tests if not set
- **TDD:** Start with failing tests, iterate to pass
- **Reuse:** Existing fixtures reused across modules
- **No mocks in integration tests**
- **Pre-commit:** All tests, lint, type-check run in pre-commit

## 7. Non-Functional Requirements

- **Incremental updates:** All pipeline steps and graph updates are idempotent and support partial re-ingestion
- **Performance:** Parallelism in pipeline, async DB access, vector search
- **Security:** All secrets in KeyVault, Entra ID auth for MCP, no hardcoded secrets
- **Auth:** Entra ID for MCP, role-based access for CLI/config
- **Observability:** Prometheus metrics, progress reporting, error logs

## 8. Workflow & Tooling Rules

- All Python env/package management via `uv`
- Linting: `ruff`
- Type checking: `pyright`
- Testing: `pytest`
- Pre-commit: all checks automated
- No direct use of pip/pipx/python outside `uv`
- All scripts/automation must enforce these rules

## 9. References

- [User/Product Requirements](99-user-product-requirements.md)
- [Python/Env Tooling Rules](../.roo/rules/01-python-uv-enforcement.md)
- [Testing Workflow](../.roo/rules/04-testing-workflow.md)
- [No Hardcoded Secrets](../.roo/rules/no-hardcoded-secrets-in-tests.md)