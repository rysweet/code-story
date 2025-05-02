## 03 Ingestion Pipeline Core (P3)

### 1 Purpose

Orchestrate **pluggable ingestion steps** in configured order, streaming status.

### 2 Responsibilities

IP‑R1 Discover steps via entry‑points · IP‑R2 obey `pipeline_order` · IP‑R3 run sequentially with shared Context · IP‑R4 publish status to Redis/REST · IP‑R5 CLI/REST triggers.

### 3 Default Order

```toml
[ingest]
pipeline_order = [
  "codestory.ingest.steps.blarify:BlarifyStep",
  "codestory.ingest.steps.fs_linker:FilesystemGraphStep",
  "codestory.ingest.steps.summariser:SummariserGraphStep"
]
```

### 4 Key Files

`pipeline.py`, `context.py`, `steps/base.py`, `steps/blarify.py`, `steps/fs_linker.py`, `steps/summariser.py`, `api.py`.

### 5 Implementation Steps

1. `poetry add docker celery redis tqdm gitpython importlib-metadata`
2. Build `PipelineStep` ABC and `PipelineRunner`.
3. Implement BlarifyStep (Docker run), FSLinkerStep, stub SummariserStep.
4. Celery task `ingest_repo`, FastAPI router, compose `worker`.

### 6 REST

POST `/v1/ingest` → `{run_id}` ; GET `/v1/status/{id}` → progress JSON.

### 7 Testing & Acceptance

* Config re‑order changes runtime order.
* 1 k‑LOC repo ingests < 60 s; failure sets state `Failed`.
