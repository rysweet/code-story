## 04 DAG & Summariser Steps (P4)

### 1 Purpose

Add two ingestion plug‑ins:

* **DAGBuilderStep** – compute module dependency DAG.
* **SummariserStep** – bottom‑up LLM summaries + embeddings.

### 2 Responsibilities

DS‑R1 build DAG in Neo4j · DS‑R3 traverse leaf→root, call OpenAI Client · DS‑R4 store `Summary` nodes & embeddings.

### 3 Implementation

1. `poetry add networkx`
2. `dag_builder.py` builds acyclic graph, writes `Module` + `DEPENDS_ON`.
3. `summariser.py` sorts, renders Jinja prompt, uses `openai_client.complete`, stores summary & vector.

### 4 Testing & Acceptance

* DAG is acyclic, summaries within token limits, pipeline progress hits 100 %.
