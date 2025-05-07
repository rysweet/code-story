# 2.0 Scaffolding

**Previous:** [Overview & Architecture](../01-overview/overview.md) | **Next:** [Configuration Module](../03-configuration/configuration.md)

**Dependencies:** None - This is a foundational component.

**Used by:** All other components

## 2.1 Purpose
Create a reproducible mono‑repo skeleton for Python 3.12 + TypeScript 5.4 development, containerized with Docker Compose and wired for CI. All later components depend on this foundation.

## 2.2 Directory Layout

```text
code-story/                  # Project root
├─ .devcontainer/            # VS Code & Codespaces
├─ .editorconfig             # Editor config
├─ .env                      # Secrets (not in repo)
├─ .env-template             # Template for secrets
├─ .codestory.toml           # Project configuration defaults
├─ .eslintrc.json            # ESLint config
├─ .github/                  # GitHub configurations
│  ├─ workflows/             # CI pipelines
│  └─ copilot-instructions.md # Copilot instructions
├─ .gitignore                # Git ignore
├─ .mypy.ini                 # Mypy config
├─ .pre-commit-config.yaml   # Pre-commit hooks
├─ .ruff.toml                # Ruff config
├─ docs/                     # Documentation (Sphinx with Markdown)
│  ├─ api/                   # Auto-generated API docs
│  ├─ architecture/          # System architecture docs
│  ├─ user_guides/           # End-user documentation
│  └─ developer_guides/      # Developer documentation
├─ gui/                      # React/Redux GUI app
│  ├─ src/                   # GUI source code
│  └─ public/                # Static assets
├─ infra/                    # Infrastructure code
│  ├─ docker/                # Dockerfiles
│  ├─ scripts/               # Infrastructure scripts
│  └─ azure/                 # Azure deployment (Bicep)
├─ prompts/                  # LLM prompt templates
├─ README.md                 # Project overview
├─ scripts/                  # Helper scripts for development
├─ specs/                    # Markdown specifications
├─ src/                      # Python package root
│  ├─ codestory/             # Core package
│  │  ├─ config/             # Configuration module
│  │  ├─ graphdb/            # Neo4j connector 
│  │  ├─ llm/                # OpenAI client
│  │  ├─ ingestion_pipeline/  # Pipeline orchestration
│  │  └─ cli/                # CLI implementation
│  ├─ codestory_service/     # FastAPI service
│  ├─ codestory_blarify/     # Blarify plugin package
│  ├─ codestory_filesystem/  # Filesystem plugin package
│  ├─ codestory_summarizer/  # Summarizer plugin package
│  └─ codestory_docgrapher/  # Documentation grapher plugin
└─ tests/                    # Test suite
   ├─ unit/                  # Unit tests
   └─ integration/           # Integration tests
```

## 2.3 Toolchain Versions

| Area       | Tool              | Version | Purpose                   |
| ---------- | ----------------- | ------- | ------------------------- |
| Python     | Poetry            | ^1.8    | Dependency & venv manager |
|            | Ruff              | latest  | Lint + format             |
|            | mypy              | latest  | Static typing (–strict)   |
|            | FastAPI           | latest  | API framework             |
|            | Celery            | latest  | Task queue                |
| JS / TS    | pnpm              | latest  | Workspace manager         |
|            | React             | ^18.0   | UI framework              |
|            | Redux Toolkit     | latest  | State management          |
|            | Mantine           | latest  | UI components             |
| Containers | Docker Engine     | ≥ 24.0  | Runtime                   |
|            | Docker Compose    | ≥ 2.0   | Multi-container orchestration |
| CI         | GitHub Actions    | n/a     | Lint + tests              |
| Dev        | devcontainer spec | 0.336.0 | Unified IDE env           |
| Observability | OpenTelemetry  | latest  | Tracing                   |
|              | Prometheus      | latest  | Metrics                   |

## 2.4 Configuration Conventions

| File                | Role                     | Precedence |
| ------------------- | ------------------------ | ---------- |
| `.env` and `.env-template` | secrets & host specifics |  1         |
| `.codestory.toml`   | project defaults         |  2         |
| hard‑coded defaults | safe fallbacks           |  3         |

The configuration module implements this priority chain and provides a singleton `settings: Settings` (Pydantic BaseSettings) accessible to all components. When `AZURE_KEYVAULT_NAME` is set, secret fields are resolved via managed identity.

## 2.5 Implementation Steps

| #  | Action                                                                               |
| -- | ------------------------------------------------------------------------------------ |
|  1 | `git init code-story && cd code-story`                                               |
|  2 | `poetry new src/codestory --name codestory`                                          |
|  3 | `poetry add pydantic rich typer[all] fastapi uvicorn celery redis neo4j openai tenacity prometheus-client structlog opentelemetry-sdk` |
|  4 | `poetry add --dev pytest pytest-asyncio pytest-cov testcontainers ruff mypy httpx pytest-mock` |
|  5 | `pnpm init -y && pnpm add -w vite react react-dom typescript @reduxjs/toolkit @mantine/core @mantine/hooks @vasturiano/3d-force-graph three` |
|  6 | Add `.env-template` with placeholders for all required secrets (`OPENAI_API_KEY`, `NEO4J_URI`, etc.) |
|  7 | Create `.codestory.toml` with default configuration values |
|  8 | Add `.pre-commit-config.yaml` with Ruff, mypy, and other linting/formatting hooks |
|  9 | Add `.github/workflows/ci.yml` for continuous integration |
| 10 | Create root `docker-compose.yaml` with all services (Neo4j, Redis, service, worker, gui, mcp) |
| 11 | Add `.devcontainer/devcontainer.json` pointing to compose services |
| 12 | Create `infra/docker/` Dockerfiles for each service component |
| 13 | Add basic documentation structure in `docs/` |
| 14 | Set up configuration module with precedence as defined in 2.4 |
| 15 | **Verification and Review** - Comprehensively verify all steps have been completed correctly:
    - Run all tests to ensure the implementation meets requirements
    - Run linting and type checking to confirm code quality
    - Verify that all services start correctly and are functional 
    - Perform thorough code review against all requirements
    - Make necessary adjustments based on review findings
    - Run tests again after any changes to ensure continued compliance
    - Document any issues encountered and their resolutions |
| 16 | Commit & push – ensure CI passes |

A helper script `scripts/bootstrap.sh` automates steps 1-14, but steps 15-16 should be performed manually.

## 2.6 Testing & Acceptance

* **Unit** – pytest; verify component functionality in isolation.
* **Integration** – Testcontainers for Neo4j and Redis; verify component interactions.
* **Lint** – Ruff, mypy (strict), ESLint for TypeScript/JavaScript.
* **Observability** – Verify metrics exposed via Prometheus endpoints; traces via OpenTelemetry.
* **Acceptance**:
  * `pytest` passes with ≥ 90% coverage on critical modules.
  * `ruff check` and `mypy --strict` pass with no errors.
  * `docker compose up -d` starts all services healthy.
  * Configuration system loads and validates settings correctly from all sources.
  * Dev container can be built and used for local development.

---

