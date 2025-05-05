# code-story – Overview & Architecture

## 1. Mission

Convert any codebase into a richly‑linked knowledge graph plus natural‑language summaries that LLM agents can query through **Model Context Protocol (MCP)**.

## 3. Data Flow Narrative

1. **CLI or GUI** triggers *Ingestion* of a codebase (local or git).
2. *Ingestion Pipeline* runs all of the steps in the ingestion workflow. Each step is a plug‑in. System can be extended by adding new plugins.
   - *BlarifyStep* runs Blarify to parse the codebase and store the raw AST in the **Graph Service**.
   - *Summariser* computes a DAG of code dependencies and walks from leaf nodes to the top and computes summaries for each module using OpenAI LLMs and stores them in the **Graph Service**.
3. *MCP Adapter* exposes the graph service to LLM agents secured by Entra ID using the [mcp-neo4j-cypher](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher) adapter.
4. *Graph Service* stores the graph and semantic index.
   - One layer of the graph is the AST and its symbol bindings, created with blarify. 
   - Another layer of the graph is the filesystem layout of the codebase.
   - Another layer of the graph is the Summary of all the modules in the codebase.
   - The semantic index is a vector database of the codebase.
   - The graph and semantic index are used to answer queries from LLM agents.
5. External agents or the **CLI/GUI** call MCP tools to query code understanding.
6. *Code-Story Service* handles the API calls and manages the ingestion pipeline.
7. *Graph Service* stores the graph and semantic index.
8. *OpenAI Client* handles the OpenAI API calls for LLM inference.

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

---