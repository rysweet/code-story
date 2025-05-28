# 11.0 Code Story Service

**Previous:** [Documentation Grapher Step](../10-docgrapher-step/docgrapher-step.md) | **Next:** [MCP Adapter](../12-mcp-adapter/mcp-adapter.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Graph Database Service](../04-graph-database/graph-database.md)
- [AI Client](../05-ai-client/ai-client.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

**Used by:**
- [CLI](../13-cli/cli.md)
- [GUI](../14-gui/gui.md)
- [MCP Adapter](../12-mcp-adapter/mcp-adapter.md)

## 11.1 Purpose

Provide a self‑hosted API service that is responsible for running the ingestion pipeline and exposing the graph service to the CLI, GUI, and MCP adapter. It will also handle the OpenAI API calls for LLM inference.  This will depend upon other components such as the Graph Database Service, Ingestion Pipeline, and OpenAI Client.  It will run in a container locally or in Azure Container Apps. The code-story service uses the **Ingestion Pipeline** library to run the ingestion pipeline and the **Graph Database Service** to query the graph database. The code-story service will also handle authentication and authorization for the REST API using Entra-ID or tokens embedded in the environment when in local dev mode. 

## 11.2 Responsibilities

- Expose a REST API for the MCP, CLI, and GUI to interact with the graph service. Including:
  - support for querying and managing graph data
  - authentication mechanisms
  - start, stop, manage status of ingestion jobs
  - manage configuration and secrets
  - health check endpoint for service, ingestion, database, and OpenAI API
  - local dev mode with token auth passed to clients through the environment
- logging and monitoring capabilities
- error handling and response formatting
- Docker container and compose file to run the service and its dependencies.
- Start and Stop scripts for the service and its supporting services.

## 11.3 Architecture and Code Structure

### 11.3.1 High-Level Design
The Code Story Service is a stateless FastAPI application that mediates between external clients (CLI, GUI, MCP) and internal subsystems (Ingestion Pipeline, Graph DB, AI Client, Config).  The design goal is to surface **every capability required by the CLI and GUI features** enumerated in sections 13 and 14 while remaining cleanly layered and portable to Azure Container Apps.

Layers (outer → inner):

1. **API Layer** – FastAPI routers (`api/`) expose:
   • Ingestion management endpoints (`/v1/ingest/*`)  
   • Graph query & Cypher execution (`/v1/query`, `/v1/query/cypher`)  
   • Natural-language ask proxy (`/v1/ask`) for GUI/CLI “ask” command  
   • Configuration CRUD (`/v1/config`) used by both CLI `cs cfg` and GUI Config Editor  
   • Service control hooks (`/v1/service/{start|stop}`) for CLI `cs ss` / `cs sx` (no-op in Prod)  
   • Health (`/v1/health`) and Prometheus `/metrics`  
   • Auth helper endpoints (`/v1/auth/login`, only in local dev)  
   All routes produce JSON:API style payloads with `data`, `meta`, `errors`.

2. **Application Layer** – orchestrators in `application/` implementing use-cases:
   • `IngestionService` – start/stop/status, streams progress over Redis PubSub → WebSocket `/ws/status/{job_id}` consumed by GUI progress panel & CLI live bar.  
   • `GraphService` – safe wrapper around Neo4j driver (read-only vs write) and high-level helpers (`find_path`, `vector_search`) that back MCP tools and `/v1/query`.  
   • `ConfigService` – loads & persists `.codestory.toml` / `.env`; fires “config-updated” event so live CLI/GUI reload their caches.  
   • `AuthService` – JWT validation in prod, passthrough token in local mode (satisfies CLI token pass-through).  

3. **Domain Layer** – pure Pydantic models: IngestionJob, StepStatus, CypherQuery, QueryResult, ConfigKey, etc.

4. **Infrastructure Layer** – adapters to external systems:
   • `Neo4jConnector`, `CeleryAdapter`, `OpenAIAdapter`, `MSALValidator`.

### 11.3.2 Package Layout
```
src/codestory_service/
├── main.py                     # FastAPI factory
├── settings.py                 # Pydantic BaseSettings
├── api/
│   ├── ingest.py               # /v1/ingest
│   ├── graph.py                # /v1/query & /v1/ask
│   ├── config.py               # /v1/config
│   ├── service.py              # /v1/service/start|stop
│   ├── health.py               # /v1/health
│   ├── auth.py                 # /v1/auth/*
│   └── websocket.py            # /ws/status/{job_id}
├── application/
│   ├── ingestion_service.py
│   ├── graph_service.py
│   ├── config_service.py
│   └── auth_service.py
├── domain/
│   ├── ingestion.py
│   ├── graph.py
│   └── config.py
└── infrastructure/
    ├── neo4j_adapter.py
    ├── celery_adapter.py
    ├── openai_adapter.py
    └── msal_validator.py
```

### 11.3.3 API ⇄ Client Capability Matrix
| Feature (CLI / GUI section)          | Endpoint / Mechanism                         | Implementation Detail |
|--------------------------------------|---------------------------------------------|-----------------------|
| Start ingestion (`cs ingest`, GUI)   | `POST /v1/ingest`                           | Enqueues Celery job; returns `job_id` |
| Live progress bar / dashboard        | `GET /ws/status/{job_id}` (WebSocket)       | Emits structured events `{step, pct}` |
| Stop/Cancel ingestion (`cs is`)      | `POST /v1/ingest/{job_id}/cancel`           | Revokes Celery task |
| List jobs (`cs ij`, GUI table)       | `GET /v1/ingest`                            | Paginated list |
| Cypher query (`cs q`)                | `POST /v1/query/cypher`                     | Accepts raw Cypher, returns rows & meta |
| MCP tool proxy (GUI playground)      | Handled by separate MCP adapter             | GraphService shared code |
| Natural-language ask (`cs ask`, GUI) | `POST /v1/ask`                              | GraphService + OpenAI embeddings |
| Config show/update (`cs cfg`, GUI)   | `GET /v1/config` / `PATCH /v1/config`       | Hot-reload when possible |
| Service start/stop (`cs ss/sx`)      | `POST /v1/service/start|stop` (dev only)    | No-ops in prod; used by CLI launcher |
| Health (`/v1/health`)               | Checks DB, Celery, Redis, OpenAI            | JSON report |
| Metrics dashboard                    | `/metrics` (Prometheus)                     | FastAPI middleware |

This mapping guarantees that every action listed in sections 13 (CLI) and 14 (GUI) is backed by a concrete HTTP or WebSocket endpoint.

### 11.3.4 Request Flow – Ingestion Run
1. CLI sends `POST /v1/ingest` with repo URL/path →  
2. `api.ingest.router` validates `IngestionRequest` →  
3. `IngestionService.start_job` publishes Celery task via `CeleryAdapter`, stores status in Redis →  
4. WebSocket `/ws/status/{job_id}` streams progress (Redis PubSub) →  
5. Job completion triggers Webhook event that GUI listens to for toast notification.

### 11.3.5 Observability
• **Logging** – structlog JSON; trace-id correlation.  
• **Metrics** – Prometheus counters for request_total, neo4j_latency, ingestion_duration.  
• **Tracing** – OpenTelemetry auto-instrumentation for FastAPI, Neo4j, Celery; exported to OTLP.

### 11.3.6 Configuration & Secrets
Precedence: *env vars* > `.env` > `.codestory.toml` > defaults.  When `AZURE_KEYVAULT_NAME` is set, secret fields are resolved via managed identity.

### 11.3.7 Local vs Azure
| Concern            | Local (Docker Compose)        | Azure Container Apps                    |
|--------------------|--------------------------------|-----------------------------------------|
| Auth               | `--no-auth` flag              | MSAL JWT validation                     |
| Neo4j              | `bolt://neo4j:7687`           | `neo4j+ssc://…` (TLS self-signed)       |
| WebSocket ingress  | Port 8000 direct              | Web App Gateway → ACA Ingress with ws   |
| Secrets            | `.env` volume                 | Key Vault reference                     |

### 11.3.8 Startup / Shutdown
```python
# filepath: src/codestory_service/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from codestory_service.infrastructure.neo4j_adapter import Neo4jConnector

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Neo4jConnector()
    await app.state.db.check()
    yield
    await app.state.db.close()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="Code Story Service")
    # mount routers…
    return app
```

## 11.4 API Endpoints

All endpoints are version-prefixed (`/v1`) and return JSON:API compliant payloads  
(`data`, `meta`, `errors`).  The request / response models listed below correspond
to Pydantic classes in `src/codestory_service/domain/*`.

### 11.4.1 Ingestion

| Method | Path                                | Request Model          | Response ‑ `200/202`                     | Notes |
|--------|-------------------------------------|------------------------|------------------------------------------|-------|
| POST   | `/v1/ingest`                        | `IngestionRequest`     | `IngestionStarted` (`202 Accepted`)      | Starts a new job and returns `job_id`; CLI `cs ingest`, GUI “Ingest” |
| GET    | `/v1/ingest`                        | —                      | `Paginated[IngestionJob]`                | List jobs; sorting & filtering supported (`status`, `repo`) |
| GET    | `/v1/ingest/{job_id}`               | —                      | `IngestionJob`                           | Get single job details |
| POST   | `/v1/ingest/{job_id}/cancel`        | —                      | `IngestionJob`                           | Attempts to cancel / revoke job |
| WebSocket | `/ws/status/{job_id}`            | —                      | stream `JobProgressEvent`                | Emits `{step, pct, message}` every ≤ 1 s |

### 11.4.2 Graph & Query

| Method | Path                   | Request Model      | Response Model          | Notes |
|--------|------------------------|--------------------|-------------------------|-------|
| POST   | `/v1/query/cypher`     | `CypherQuery`      | `QueryResult`           | Raw Cypher; returns columns/rows |
| POST   | `/v1/query/vector`     | `VectorQuery`      | `VectorResult`          | Semantic / embedding search |
| POST   | `/v1/query/path`       | `PathRequest`      | `PathResult`            | Shortest / k-paths between nodes |

### 11.4.3 Natural-Language “Ask”

| Method | Path      | Request Model | Response Model | Notes |
|--------|-----------|---------------|----------------|-------|
| POST   | `/v1/ask` | `AskRequest`  | `AskAnswer`    | Delegates to OpenAI + GraphService; backs CLI `cs ask` & GUI “Ask” |

### 11.4.4 Configuration

| Method | Path            | Request Model   | Response Model        | Notes |
|--------|-----------------|-----------------|-----------------------|-------|
| GET    | `/v1/config`    | —               | `ConfigDump`          | Full config; sensitive keys redacted |
| PATCH  | `/v1/config`    | `ConfigPatch`   | `ConfigDump`          | Partial update; hot-reload when safe |
| GET    | `/v1/config/schema` | —           | `ConfigSchema`        | JSON Schema used by GUI form generation |

### 11.4.5 Service Control (dev-only)

| Method | Path                       | Notes |
|--------|----------------------------|-------|
| POST   | `/v1/service/start`        | CLI `cs ss`; no-op in prod |
| POST   | `/v1/service/stop`         | CLI `cs sx`; no-op in prod |

### 11.4.6 Authentication

| Method | Path            | Purpose                              |
|--------|-----------------|--------------------------------------|
| POST   | `/v1/auth/login`| Local-dev token mint (username / pwd) |
| GET    | `/v1/auth/whoami` | Echo back current principal claims |

### 11.4.7 Health & Observability

| Method | Path          | Response | Notes |
|--------|---------------|----------|-------|
| GET    | `/v1/health`  | `HealthReport` | DB, Celery, Redis, OpenAI, build SHA |
| GET    | `/metrics`    | Prometheus text | Exposed via Starlette middleware |

### 11.4.8 Error Handling

All errors return a JSON array under `errors` following RFC 9457:  

```json
{
  "errors": [
    {
      "status": "404",
      "title": "Job Not Found",
      "detail": "No ingestion job with id '8cbb…' exists",
      "meta": {"job_id": "8cbb…"}
    }
  ]
}
```

Standard HTTP codes: `400` validation, `401/403` auth, `404` missing,
`409` conflict, `500` unhandled.


## 11.5 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to be able to run the code-story service in a container so that I can develop and test the service locally. | • The code-story service can be started and stopped using the provided scripts.<br>• The code-story service can be queried using the REST API. |
| As a developer, I want to be able to run the code-story service in Azure Container Apps so that I can deploy the service in Azure. | • The code-story service can be started and stopped using the provided scripts.<br>• The code-story service can be queried using the REST API. |
| As a developer, I want to query and manage graph data using cypher queries through a REST API so that I can interact with the graph service programmatically. | • The REST API provides endpoints for querying and managing graph data with cypher queries.<br>• Queries return correctly formatted responses. |
| As a developer, I want to use vector search capabilities to find semantically similar content in the graph. | • The `/v1/query/vector` endpoint accepts semantic search parameters.<br>• Vector search results include relevance scores and content snippets. |
| As a developer, I want to perform path finding between graph nodes so I can understand relationships in the codebase. | • The `/v1/query/path` endpoint successfully finds paths between specified nodes.<br>• Path results include all intermediate nodes and relationships. |
| As a developer, I want to ask natural language questions about the codebase and get meaningful answers. | • The `/v1/ask` endpoint accepts natural language questions.<br>• Responses combine graph data with LLM-generated explanations. |
| As a developer, I want Entra-ID authentication mechanisms for the REST API so that I can secure access to the graph service. | • The REST API endpoints require valid authentication tokens.<br>• Unauthorized requests are rejected with appropriate HTTP status codes. |
| As a developer, I want to start, stop, and manage the status of ingestion jobs via the REST API so that I can control ingestion workflows. | • The REST API provides endpoints to start, stop, and check the status of ingestion jobs.<br>• Job statuses are accurately reported. |
| As a developer, I want to receive real-time ingestion progress updates so I can monitor long-running jobs. | • The WebSocket endpoint `/ws/status/{job_id}` streams progress events.<br>• Progress events include step name, completion percentage, and status messages. |
| As a developer, I want to manage configuration and secrets through the REST API so that I can dynamically adjust service settings. | • The REST API provides endpoints to retrieve and update configuration and secrets.<br>• Configuration changes take effect without service restarts when possible. |
| As a developer, I want to control service lifecycle (start/stop) via the API so the CLI and other clients can manage services. | • The `/v1/service/start` and `/v1/service/stop` endpoints function correctly in dev mode.<br>• Service control endpoints are safely disabled in production. |
| As a developer, I want a health check endpoint so that I can verify the operational status of the service, ingestion pipeline, database, and OpenAI API. | • The health check endpoint accurately reports the status of all components.<br>• Health check responses clearly indicate the status of each component. |
| As a developer, I want logging and monitoring capabilities so that I can observe and troubleshoot the service effectively. | • Logs are generated for key events and errors.<br>• Monitoring metrics are exposed through the `/metrics` endpoint for Prometheus integration. |
| As a developer, I want consistent error handling and response formatting so that I can reliably handle API responses. | • Errors are returned with clear, consistent formatting following JSON:API standards.<br>• API responses follow the documented schema with `data`, `meta`, and `errors` sections. |
| As a developer, I want a local development mode with token authentication passed through the environment so that I can easily test the service locally. | • Local development mode can be enabled via configuration.<br>• Authentication tokens are correctly passed and validated in local mode. |


## 11.6 Testing Strategy

- **Unit** - unit tests for each method of API
- **Integration** - integration tests depend on the actual database and OpenAI API. Ensure that the service can be started and stopped successfully. Ensure that the service can be queried successfully. Ensure that the service can be queried with cypher queries successfully. Validate all acceptance criteria.

## 11.7 Implementation Steps
1. **Set up project structure**
   - Create the directory structure as outlined in section 11.3.2
   - Set up a dedicated Python package `codestory_service`
   - Create empty `__init__.py` files in all directories

2. **Install dependencies**
   ```bash
   poetry add fastapi uvicorn pydantic python-multipart websockets aioredis prometheus-client structlog opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp neo4j celery redis msal
   poetry add --dev pytest pytest-asyncio httpx pytest-cov pytest-mock
   ```

3. **Implement infrastructure layer**
   - Implement `neo4j_adapter.py` with:
     - Connection pooling to efficiently manage Neo4j connections
     - Retry logic with exponential backoff for transient failures
     - Connection lifecycle management (graceful open/close)
     - Metrics for connection performance and errors
   - Implement `celery_adapter.py` for task queue operations
   - Implement `openai_adapter.py` for LLM interactions
   - Implement `msal_validator.py` for token validation

4. **Implement domain models**
   - Create Pydantic models in `domain/ingestion.py`, `domain/graph.py`, and `domain/config.py`
   - Include validators and custom methods for domain operations
   - Add proper typing for all models

5. **Implement application services**
   - Implement `graph_service.py` as a thin façade over `neo4j_adapter.py`, focusing on business logic rather than connection details
   - Implement `ingestion_service.py` for pipeline orchestration
   - Implement `config_service.py` for reading/writing configuration
   - Implement `auth_service.py` for authentication logic

6. **Implement API layer**
   - Create the API routers in `api/` with proper endpoint handlers
   - Implement websocket handler for real-time progress updates
   - Add middleware for authentication, logging, and metrics

7. **Implement app factory and settings**
   - Create `main.py` with FastAPI app factory
   - Implement `settings.py` with configuration management
   - Set up lifespan context managers for resource management

8. **Set up Docker environment**
   - Create `Dockerfile` for the service
   - Add service to project-level `docker-compose.yaml`
   - Configure environment variables and volumes

9. **Write unit tests**
   - Create tests for each component with high coverage
   - Mock external dependencies appropriately
   - Test both success and error paths

10. **Write integration tests**
    - Create tests that verify interaction between components
    - Test end-to-end API flows with test fixtures
    - Verify WebSocket functionality

11. **Implement observability**
    - Set up structured logging with request correlation
    - Configure Prometheus metrics endpoint
    - Add OpenTelemetry tracing

12. **Create helper scripts**
    - Write startup script for local development
    - Create healthcheck utility
    - Add database initialization script

13. **Documentation**
    - Add docstrings to all public functions and classes
    - Create OpenAPI documentation
    - Add README with usage instructions

14. **Quality checks**
    - Run linting and formatting
    - Perform static type checking
    - Validate against security best practices

15. **Deployment verification**
    - Test local deployment with Docker Compose
    - Verify Azure Container Apps compatibility
    - Ensure proper secret handling in both environments

16. **Verification and Review**
    - Run all unit, integration, and end-to-end tests
    - Verify test coverage meets targets (≥90% for critical components) 
    - Run linting and type checking on all code
    - Start the service and verify all endpoints function correctly
    - Test WebSocket functionality for real-time updates
    - Verify authentication works in both development and production modes
    - Test all error paths and failure scenarios
    - Perform thorough code review against requirements and design principles
    - Validate handling of concurrent requests and connection lifecycles
    - Test performance under load, especially for graph operations
    - Make necessary adjustments based on review findings
    - Re-run all tests after any changes
    - Document discovered issues and their resolutions

17. **Acceptance criteria validation**
    - Verify all user stories in section 11.5 are satisfied
    - Run a full system test covering all endpoints
    - Document any limitations or known issues
    - Create detailed PR for final review

---

## Error Logging and Propagation

- All service errors must be recorded to a persistent error log on the server (e.g., `/var/log/codestory/error.log`).
- On any endpoint invocation, the service checks the error log for new entries since the last request.
- If new errors are found, the service includes an `error_package` in the response payload with the error messages and clears the processed entries from the log.
- Consumers can use the `error_package` to detect and handle service-side failures.

## Health Check Extensions

- The `/health` endpoint returns any unreported errors in the `error_package` field:

```json
{
  "status": "unhealthy",
  "error_package": [
    "Traceback ...",
    "Detail ..."
  ],
  "components": { ... }
}
```

