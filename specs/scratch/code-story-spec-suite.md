<!-- code-story – Specification Suite (v0.3) -->

# code-story – Overview & Architecture

## 1. Mission

Convert any codebase into a richly‑linked knowledge graph plus natural‑language summaries that LLM agents can query through **Model Context Protocol (MCP)**.

## 3. Components and Data Flow

1. **CLI or GUI** triggers *Ingestion* of a codebase (local or git). Alternatively queries or displays the graph or nodes/edges/metadata from the graph. 
   - *CLI* is a rich command line interface using [Rich](https://github.com/Textualize/rich-cli). 
   - *GUI* is a React + Redux web application that uses the 3D force graph library to display the graph and allows users to interact with it.
   - *CLI* and *GUI* are both built using the same codebase and consume the same API from the **Code-Story Service**.
2. *Code-Story Service* python service runs in a container and handles the API calls and manages the ingestion pipeline or queries the graph service.
   - *Ingestion Pipeline* is a Celery task queue and workers for running the ingestion pipeline.
   - *Graph Service* is a Neo4j graph database and semantic indexing service that stores the graph and semantic index.
   - *OpenAI Client* is an Azure OpenAI client for LLM inference.
3. *Ingestion Pipeline* runs all of the steps in the ingestion workflow. Each step is a plug‑in. System can be extended by adding new plugins.
   - *BlarifyStep* runs [Blarify](https://github.com/blarApp/blarify) to parse the codebase and store the raw AST in the **Graph Service**.
   - *Summariser* computes a DAG of code dependencies and walks from leaf nodes to the top and computes summaries for each module using the Azure AI model endpoints and stores them in the **Graph Service**.
   - *FileSystemStep* creates a graph of the filesystem layout of the codebase and links it to the AST nodes.
   - *DocumentationGrapher* creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes.
4. *MCP Adapter* exposes the graph service to LLM agents [secured by Entra ID](https://den.dev/blog/auth-modelcontextprotocol-entra-id/) using the [mcp-neo4j-cypher](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher) adapter. Also see 
5. *Graph Service* stores the graph and semantic index.
   - uses Neo4j 5.x with the native vector store and semantic indexing.
   - uses [APOC](https://neo4j.com/labs/apoc/)
   - One layer of the graph is the AST and its symbol bindings, created with blarify. 
   - Another layer of the graph is the filesystem layout of the codebase.
   - Another layer of the graph is the Summary of all the modules in the codebase.
   - The semantic index is a vector database of the codebase - see [Neo4j Blog on Semantic indexes](https://neo4j.com/blog/developer/knowledge-graph-structured-semantic-search/)
   - The graph and semantic index are used to answer queries from LLM agents.
6. External agents or the **CLI/GUI** call MCP tools to query code understanding.
7. *OpenAI Client* handles the OpenAI API calls for LLM inference. Will use ```az login --scope https://cognitiveservices.azure.com/.default``` with bearer token auth in the AzureOpenAI package to authenticate and use the Azure OpenAI API. The client will be a thin wrapper around the Azure OpenAI API and will handle the authentication and request/response handling, as well as backoff/throttling strategies. The client will also support asynchronous requests to improve performance and scalability. 
8. Docs - use Sphinx to generate docs from the codebase and its docstrings. There will also be Markdown documentation for each of the modules and components. 

## 4. Deployment Topology (local dev)

1. Neo4J Graph Service - runs in a container - Neo4j graph database and semantic indexing.
2. Blarify container - linux container running blarify to parse the codebase and populate the graph database.
3. Code-Story Service - Hosts the APIs for the core functionality of Ingestion and Querying the graph database.
4. CLI - Rich CLI for interacting with the code-story service.
5. GUI - React + Redux GUI for interacting with the code-story service.
6. OpenAI Client - Azure OpenAI client for LLM inference.
7. Ingestion Pipeline - Celery task queue and workers for running the ingestion pipeline.
8. MCP Adapter - use https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher to expose the graph database as a MCP service.


All services run under `docker-compose` network; Azure Container Apps deployment mirrors this layout with container scaling.

## 5. Cross‑Cutting Concerns

* **Auth**: MCP endpoints protected by Entra ID bearer JWT; local mode can bypass with `--no-auth` flag.
* **Observability**: OpenTelemetry traces, Prometheus metrics from every service, Grafana dashboard template in `infra/`.
* **Extensibility**: Ingestion steps are plug‑in entry‑points; GUI dynamically reflects new step types; prompts in `prompts/` folder can be customised.


## 00 Scaffolding (P0)

\### 1 Purpose
Create a reproducible mono‑repo skeleton for Python 3.12 + TypeScript 5.4 development, containerised with Docker Compose and wired for CI. All later components depend on this foundation.

\### 2 Directory Layout

```text
code-story/
├─ .devcontainer/            # VS Code & Codespaces
├─ .github/workflows/        # CI pipelines
├─ cli/                      # Typer + Rich CLI (added P6)
├─ docs/                     # MkDocs site (added P9)
├─ gui/                      # React/Redux app (added P7)
├─ infra/                    # Docker, compose, Bicep (added P8)
├─ prompts/                  # Prompty templates
├─ specs/                    # Markdown specifications (this file)
├─ src/                      # Python package root
│  └─ codestory/
└─ tests/                    # pytest + testcontainers
```

\### 3 Toolchain Versions

| Area       | Tool              | Version | Purpose                   |
| ---------- | ----------------- | ------- | ------------------------- |
| Python     | Poetry            | ^1.8    | Dependency & venv manager |
|            | Ruff              | latest  | Lint + format             |
|            | mypy              | latest  | Static typing (–strict)   |
| JS / TS    | pnpm              | latest  | Workspace manager         |
| Containers | Docker Engine     | ≥ 24.0  | Runtime                   |
| CI         | GitHub Actions    | n/a     | Lint + tests              |
| Dev        | devcontainer spec | 0.336.0 | Unified IDE env           |

\### 4 Configuration Conventions

| File                | Role                     | Precedence |
| ------------------- | ------------------------ | ---------- |
| `.env`              | secrets & host specifics |  1         |
| `.codestory.toml`   | project defaults         |  2         |
| hard‑coded defaults | safe fallbacks           |  3         |

`src/codestory/config.py` exposes a singleton `settings: Settings` (Pydantic BaseSettings).

\### 5 Implementation Steps

| #  | Action                                                                               |
| -- | ------------------------------------------------------------------------------------ |
|  1 | `git init code-story && cd code-story`                                               |
|  2 | `poetry new src/codestory --name codestory`                                          |
|  3 | `poetry add pydantic rich typer[all] testcontainers pytest pytest-asyncio ruff mypy` |
|  4 | `pnpm init -y && pnpm add -w vite typescript @types/node`                            |
|  5 | Add `.env.example` placeholders (`OPENAI_API_KEY=` etc.)                             |
|  6 | Add `.pre-commit-config.yaml` – Ruff + mypy                                          |
|  7 | Add `.github/workflows/ci.yml` – setup‑python, `poetry install`, Ruff, mypy, pytest  |
|  8 | Root `docker-compose.yaml` with Neo4j & Redis stubs                                  |
|  9 | `.devcontainer/devcontainer.json` pointing to compose services                       |
| 10 | Commit & push – CI green                                                             |

A helper script `scripts/bootstrap.sh` may automate steps 1‑9.

\### 6 Testing & Acceptance

* **Unit** – pytest; verify config precedence & validation.
* **Lint** – Ruff, mypy (strict).
* **Acceptance**

  * `pytest` passes ≥ 90 % coverage on P0 modules.
  * `ruff check` clean; `mypy --strict` clean.
  * `docker compose up -d` starts Neo4j & Redis healthy.

---

\## 01 Graph Service (P1)

\### 1 Purpose
Provide a self‑hosted **Neo4j 5.x** backend with:

* AST/symbol nodes from Blarify
* File‑system nodes
* Summary & embedding nodes
* **Semantic Index** (full‑text + vector) for combined structured + similarity search
* Thin Python client + REST façade consumed by Ingestion (P3 + P4) and MCP Adapter (P5).

\### 2 Responsibilities

| ID     | Responsibility                                                              |
| ------ | --------------------------------------------------------------------------- |
|  GS‑R1 | Migrate & initialise Neo4j schema (constraints, APOC, GDS plugin).          |
|  GS‑R2 | Create/update **semantic index** combining property‐graph and vector store. |
|  GS‑R3 | Connection‑pooling & retry logic exposed via `GraphService` Python class.   |
|  GS‑R4 | Expose lightweight REST API (`/v1/query`, `/v1/vectorSearch`) with AuthZ.   |
|  GS‑R5 | Emit OpenTelemetry spans & Prometheus metrics for every query.              |

\### 3 Architecture

```
┌──────────────────────────────┐
│  src/codestory/graph/        │
│  ├── __init__.py             │  ← public façade
│  ├── service.py              │  ← GraphService class
│  ├── models.py               │  ← pydantic DTOs
│  ├── schema.cypher           │  ← DDL + constraints
│  ├── migrations/             │  ← y‑y‑m‑d_*.cypher files
│  └── api.py                  │  ← FastAPI router
└──────────────────────────────┘
```

Deployed inside `docker‑compose` as **neo4j** service (`neo4j:5‑enterprise`) with mounted `plugins/` (APOC, n10s). Data persisted in named volume `neo4j_data`.

\### 4 Data Model (abridged)

| Label         | Key Props                                                                 | Notes           |
| ------------- | ------------------------------------------------------------------------- | --------------- |
| `File`        | `path`, `sha`, `commit_ts`                                                | filesystem node |
| `Symbol`      | `fqname`, `lang`, `kind`                                                  | AST element     |
| `Summary`     | `uuid`, `text`, `embedding` (vector)                                      | produced by P4  |
| `Repo`        | `repo_id`, `host`                                                         | top‑level       |
| Relationships |  `(:File)-[:DECLARES]->(:Symbol)`<br>`(:Summary)-[:DESCRIBES]->(:Symbol)` |                 |

\### 5 Public API Contracts
\#### Python (sync & async)

```python
from codestory.graph import GraphService

svc = GraphService()
svc.ensure_schema()
cypher = "MATCH (f:File) RETURN count(f) AS n"
print(svc.run(cypher)[0].n)

rows = await svc.vector_search("http server handler", top_k=10)
```

\#### REST

| Method | Path               | Body                             | Resp                | Notes        |
| ------ | ------------------ | -------------------------------- | ------------------- | ------------ |
| POST   | `/v1/query`        | `{ cypher: str, params?: dict }` | JSON rows           | Admin‑only   |
| POST   | `/v1/vectorSearch` | `{ text: str, top_k?: int }`     | `[ {node, score} ]` | Bearer token |

\### 6 Implementation Steps (dependency → P0)

| #  | Task                                                                                                                    |
| -- | ----------------------------------------------------------------------------------------------------------------------- |
|  1 | Add Poetry deps: `neo4j[bolt]`, `fastapi`, `uvicorn[standard]`, `opentelemetry‑api`, `prometheus‑client`                |
|  2 | Write `schema.cypher` (uniqueness constraints, vector index powered by native Vector 50).                               |
|  3 | Implement `GraphService` with lazy singleton driver, `run`, `vector_search`, `ensure_schema`.                           |
|  4 | Build FastAPI router `api.py` mounting under `/v1`; integrate MSAL token verifier (delegates to P5 later).              |
|  5 | Extend `docker-compose.yaml`: add neo4j service + bolt env + apoc plugin download. Start service healthcheck script.    |
|  6 | Add Makefile target `make graph-shell` – opens cypher‑shell inside container.                                           |
|  7 | Create Alembic‑like migration runner (`python -m codestory.graph.migrate`) that executes any new `migrations/*.cypher`. |
|  8 | Wire OTEL & metrics (middleware).                                                                                       |

\### 7 Testing Strategy

* **Unit** – mock `neo4j.Driver`; assert Cypher generated; test vector search param build.
* **Integration (docker‑compose)**

  1. Spin neo4j container with test volume
  2. Run `ensure_schema()` – assert indexes appear (`CALL db.indexes`)
  3. Store dummy node with embedding → query `/v1/vectorSearch` returns hit ≈ 1.0

\### 8 Acceptance Criteria

* `pytest -m integration` passes inside CI using **testcontainers‑python** (Neo4j 5).
* Schema migration idempotent (second run no errors).
* REST `/v1/vectorSearch` P99 latency < 150 ms on dev laptop for 100‑node sample.

\### 9 One‑Shot Code Generation Instructions

> **Prompt header**: “You are generating the Graph Service module (‘P1’) for code‑story…”
> **Include**: files listed in Architecture §3, Poetry additions (Step 1), `docker-compose` patch (Step 5), and full unit+integration tests.
> **Assume**: P0 scaffold exists.
> **Stop** after emitting `### END`.

---

## 02 OpenAI Client (P2)

### 1 Purpose

Expose a thin, resilient wrapper around **Azure OpenAI** that any other component can call for **completions, embeddings, or chat**.
*It does **not** own domain‑specific summarisation logic – that belongs to the **Summariser Step** in P4.*

### 2 Responsibilities

| ID     | Description                                                                                                                                                                                                                |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP-R1 | Implement MCP Tool Server spec (gRPC + HTTP) backed by GraphService queries.                                                                                                                                               |
| MCP-R2 | Secure endpoints with Microsoft Entra ID (MSAL) using auth flow described in [https://den.dev/blog/auth-modelcontextprotocol-entra-id/](https://den.dev/blog/auth-modelcontextprotocol-entra-id/) (bearer JWT validation). |
| MCP-R3 | Map high‑level MCP tool names to Cypher queries and vector searches: `searchGraph`, `summarizeNode`, `pathTo`, `similarCode`.                                                                                              |
| MCP-R4 | Provide usage quota & basic analytics (requests, latency) exposed via Prometheus.                                                                                                                                          |
| MCP-R5 | Package as FastAPI app runnable inside docker‑compose and Azure Container Apps.                                                                                                                                            |

### 3 Architecture

```
src/codestory/mcp/
├── __init__.py
├── server.py          # FastAPI + gRPC reflection
├── auth.py            # Entra ID JWT verification + caching
├── tools/
│   ├── base.py        # Tool abstraction
│   ├── search_graph.py
│   ├── summarize_node.py
│   ├── path_to.py
│   └── similar_code.py
└── proto/             # MCP proto files (vendored)
```

Container image `codestory-mcp` built from repo root `Dockerfile.mcp`.

### 4 Public Endpoints

| Protocol    | URL                     | Description                          |
| ----------- | ----------------------- | ------------------------------------ |
| HTTP/2 gRPC | `/mcp.ToolService/*`    | Standard MCP RPCs                    |
| REST        | `/v1/tools/searchGraph` | Mirror of gRPC methods for debugging |
| REST        | `/metrics`              | Prometheus exposition                |

### 5 Implementation Steps

| # | Task                                                                                           |
| - | ---------------------------------------------------------------------------------------------- |
| 1 | `poetry add fastapi uvicorn[standard] grpcio grpcio-tools msal jose prometheus-client`         |
| 2 | Compile MCP protos into `src/codestory/mcp/proto_gen/` via `grpcio-tools`.                     |
| 3 | Implement `auth.py` – cache JWKS, validate access tokens, enforce `graph.read` scope.          |
| 4 | Implement Tool classes each exposing `handle(request) -> response` using GraphService methods. |
| 5 | Wire FastAPI routes + gRPC server (using `grpclib` or native gRPC) sharing auth dependency.    |
| 6 | Add Compose service `mcp` listening on 0.0.0.0:9000 (gRPC) and :8080 (REST).                   |

### 6 Testing Strategy

* **Unit** – mock GraphService; test each tool handler returns expected payload.
* **Auth** – generate signed JWT with test key; ensure `auth.verify` accepts valid token and rejects invalid scope.
* **Integration** – compose Neo4j + MCP; run gRPC client call `searchGraph` and assert JSON reply.

### 7 Acceptance Criteria

* gRPC `searchGraph` round‑trip latency < 200 ms for simple query on dev laptop.
* Invalid token returns HTTP 401 / gRPC `UNAUTHENTICATED`.
* Prometheus metrics endpoint lists `mcp_requests_total` counter.

### 8 One‑Shot Code Generation Instructions

> **Prompt header**: “Generate the MCP Adapter module (‘P5’) for code‑story.”
> **Include**: all files listed in Architecture §3, Dockerfile.mcp, compose service, unit & integration tests, and minimal docs.
> **Assume**: P0–P4 implemented.
> **Finish** with `### END`.

## 06 CLI (P6)

### 1 Purpose

Offer a **Rich/Typer-based** command‑line interface enabling developers to:

* Trigger ingestion runs
* Tail live progress with Rich live tables/spinners
* Query graph summaries (`search`, `path`, etc.)
* Edit configuration files interactively
* Launch the GUI in browser

### 2 Commands

| Command                          | Alias    | Description                                                |                                     |
| -------------------------------- | -------- | ---------------------------------------------------------- | ----------------------------------- |
| `codestory ingest <path-or-url>` | `cs in`  | Kick off ingestion and stream progress bar.                |                                     |
| `codestory status <run-id>`      | `cs st`  | Show status table for a previous run.                      |                                     |
| \`codestory query \<cypher       | mcp>\`   | `cs q`                                                     | Run ad‑hoc Cypher or MCP tool call. |
| `codestory config edit`          | `cs cfg` | Open interactive TUI to modify `.codestory.toml` / `.env`. |                                     |
| `codestory ui`                   | `cs ui`  | Open GUI (P7) at `http://localhost:5173`.                  |                                     |

### 3 Implementation Steps

1. `poetry add typer rich rich-markdown rich-click`
2. Create `cli/__main__.py` registering Typer app.
3. Use Rich live progress: subscribe to Redis `status::<run_id>`.
4. Implement config TUI via `rich.prompt` + TOML editing.
5. Package entry‑point in `pyproject.toml` → `console_scripts = { codestory = 'codestory.cli:app' }`.

### 4 Testing

* **Unit** – invoke Typer CLI runner to ensure commands parse.
* **Integration** – start compose stack, run `codestory ingest tests/fixtures/repo`, expect 0 exit and spinner.

### 5 Acceptance Criteria

* Typing `cs in .` on fresh repo prints colored progress and ends with green “Completed”.
* `cs q "MATCH (n) RETURN count(n)"` returns Rich table.

### 6 One-Shot Code Generation Instructions

> Prompt: “Generate the CLI module (‘P6’) for code-story…” — include all files, tests, and docs; assume P0–P5 present.

---

## 07 GUI (P7)

### 1 Purpose

Provide a **React + Redux** single‑page application that visualises the Neo4j graph in 3‑D (using `3d-force-graph`), lets users control ingestion runs, query graph data, and edit configuration.

### 2 Key Features

* 3‑D force‑directed graph view with Neo4j integration, showing node/edge metadata on hover.
* Ingestion dashboard: start run, show progress per step.
* Config editor form bound to `.env` / `.codestory.toml` via REST.
* MCP playground tab to issue tool calls and view JSON.

### 3 Tech Stack

* Vite + React 18 + TypeScript 5
* Redux Toolkit + RTK Query
* Mantine UI components; `3d-force-graph` for visualisation
* Axios for API calls; WebSocket for live progress

### 4 Implementation Steps

1. `pnpm create vite gui --template react-ts`
2. Add deps: `redux toolkit`, `react-redux`, `mantine`, `@vasturiano/force-graph`, `three`, `axios`.
3. Set up RTK store slices: `graphApi`, `ingestApi`, `configSlice`.
4. Build `GraphViewer` component that queries `/v1/query` for subgraph, feeds to force‑graph, and opens side‑panel on click.
5. Build `IngestionPanel` subscribing to WebSocket `/ws/status`.
6. Config editor writes JSON to `/v1/config` which CLI & services read.
7. Deploy dev server on port 5173; include Dockerfile `gui.Dockerfile` for production build.

### 5 Testing

* **Cypress component tests** for `GraphViewer` interaction.
* Mock REST with MSW for unit tests.

### 6 Acceptance Criteria

* Able to load medium‑size graph (≤ 5k nodes) at 60 FPS on modern GPU browser.
* Starting ingestion via GUI shows real‑time progress.

### 7 One-Shot Code Generation Instructions

> Prompt: “Generate the GUI (P7) for code-story…” — include Vite config, React code, Dockerfile, Cypress tests; assume backend is running.

---

## 08 Infra Module (P8)

### 1 Purpose

Provide infrastructure‑as‑code for local Docker‑Compose **and** Azure Container Apps deployment.

### 2 Deliverables

* `docker-compose.yaml` (services: neo4j, redis, worker, mcp, gui)
* `Dockerfile` for Python services; `Dockerfile.gui`
* `bicep/aca.bicep` template deploying services + secrets mapping
* `devcontainer.json` for Codespaces/local VS Code

### 3 Implementation Steps

1. Write compose with correct networks & healthchecks.
2. Provide `make local-up` / `make local-down`.
3. Add Bicep template param files; docs on `az containerapp` deploy.

### 4 Acceptance Criteria

* `docker compose up -d` brings full stack healthy.
* `az deployment sub create -f bicep/aca.bicep` succeeds.

### 5 Code Generation Instructions

> Prompt: “Generate Infra module (‘P8’)…”.

---

## 09 Docs & Prompts (P9)

### 1 Purpose

Ship user and developer documentation plus reusable Prompty prompt templates.

### 2 Components

* `docs/` MkDocs site with nav: Overview, Install, CLI, GUI, API, MCP.
* `prompts/` – Jinja templates for module summaries, chat system prompts, etc.
* `CHANGELOG.md`, `CONTRIBUTING.md`.

### 3 Implementation Steps

1. `poetry add mkdocs-material mkdocs-mermaid2-plugin`
2. Create `mkdocs.yml`; enable mermaid.
3. Add GitHub Pages deploy action.

### 4 Acceptance Criteria

* `mkdocs serve` opens docs site locally.
* Each prompt file contains instructions and placeholders.

### 5 Code Generation Instructions

> Prompt: “Generate Docs & Prompts module (‘P9’) for code-story…”

---
