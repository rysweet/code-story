## 01 Graph Service (P1)

### 1 Purpose

Provide a self‑hosted **Neo4j 5.x** backend with semantic index and vector search, plus a thin Python/REST façade for other components.

### 2 Responsibilities

| ID    | Responsibility                                                         |
| ----- | ---------------------------------------------------------------------- |
| GS-R1 | Create schema, constraints, vector & full‑text indexes.                |
| GS-R2 | Expose `GraphService` class (`run`, `vector_search`, `ensure_schema`). |
| GS-R3 | Provide REST endpoints `/v1/query`, `/v1/vectorSearch`.                |
| GS-R4 | Emit OTel spans & Prometheus metrics.                                  |

### 3 Architecture

```
src/codestory/graph/
├── __init__.py
├── service.py      # GraphService singleton
├── models.py       # pydantic DTOs
├── schema.cypher   # DDL
├── migrations/
└── api.py          # FastAPI router
```

### 4 Data Model (excerpt)

* `(:File {path, sha, commit_ts})`
* `(:Symbol {fqname, lang, kind})`
* `(:Summary {uuid, text, embedding})`
* Relationships: `DECLARES`, `DESCRIBES`, etc.

### 5 Implementation Steps

1. `poetry add neo4j fastapi uvicorn[standard] opentelemetry-api prometheus-client`
2. Write `schema.cypher` & migrations runner.
3. Implement `GraphService` with bolt driver pool.
4. Build REST router; integrate auth in P5.
5. Extend compose: `neo4j:5-enterprise` + APOC.

### 6 Testing & Acceptance

* Integration test ensures vector index exists and `/v1/vectorSearch` returns a hit.
* Schema migration idempotent.
