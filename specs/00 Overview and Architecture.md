# code-story – Overview & Architecture

## 1. Mission

Convert any codebase into a richly‑linked knowledge graph plus natural‑language summaries that LLM agents can query through **Model Context Protocol (MCP)**.

## 2. High‑Level Component Map

| Tag | Layer                  | Key Tech                      | Spec Doc                   |
| --- | ---------------------- | ----------------------------- | -------------------------- |
| P0  | **Scaffolding**        | Poetry, pnpm, Docker Compose  | `00_scaffolding.md`        |
| P1  | **Graph Service**      | Neo4j 5.x, APOC, vector index | `01_graph_service.md`      |
| P2  | **OpenAI Client**      | Azure OpenAI, Prometheus      | `02_openai_client.md`      |
| P3  | **Ingestion Pipeline** | Celery, Docker‑exec Blarify   | `03_ingestion_pipeline.md` |
| P4  | **DAG & Summariser**   | NetworkX, OpenAI              | `04_dag_summariser.md`     |
| P5  | **MCP Adapter**        | FastAPI, gRPC, Entra ID       | `05_mcp_adapter.md`        |
| P6  | **CLI**                | Rich + Click                  | `06_cli.md`                |
| P7  | **GUI**                | React + Redux, 3d‑force‑graph | `07_gui.md`                |
| P8  | **Infra**              | Docker Compose, Bicep/ACA     | `08_infra.md`              |
| P9  | **Docs & Prompts**     | MkDocs, Prompty               | `09_docs_prompts.md`       |

## 3. Data Flow Narrative

1. **CLI/GUI** triggers *Ingestion* (P3).
2. *BlarifyStep* parses repo → raw AST stored in **Graph Service** (P1).
3. *DAGBuilder* & *Summariser* (P4) enrich graph with module DAG, summaries, embeddings.
4. **MCP Adapter** (P5) exposes read‑only graph tools secured by Entra ID.
5. External agents or the **CLI/GUI** call MCP tools to query code understanding.

## 4. Deployment Topology (local dev)

```
┌──────────────┐          ┌──────────────┐
│  GUI (P7)    │◀────HTTP▶│  MCP (P5)    │◀──gRPC──┐
└──────────────┘          └──────────────┘        │
        ▲                        ▲                │
        │                        │ REST/WS        │
        │                        ▼                │
┌──────────────┐    pushes  ┌──────────────┐      │
│  CLI (P6)    │──────────▶ │ Ingestion P3 │      │
└──────────────┘  progress   └──────────────┘      │
                                   │ Cypher        │
                                   ▼               │
                             ┌──────────────┐      │
                             │ Neo4j (P1)   │◀─────┘
                             └──────────────┘
```

All services run under `docker-compose` network; Azure Container Apps deployment mirrors this layout with container scaling.

## 5. Cross‑Cutting Concerns

* **Auth**: MCP endpoints protected by Entra ID bearer JWT; local mode can bypass with `--no-auth` flag.
* **Observability**: OpenTelemetry traces, Prometheus metrics from every service, Grafana dashboard template in `infra/`.
* **Extensibility**: Ingestion steps are plug‑in entry‑points; GUI dynamically reflects new step types; prompts in `prompts/` folder can be customised.

---

*For implementation details of each component, open the corresponding spec file listed above.*
