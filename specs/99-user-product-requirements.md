# Code Story User & Product Requirements

## Overview & Architecture
- Convert any codebase into a richly-linked knowledge graph plus natural-language summaries that developers can query through:
  - CLI with a rich command-line interface  
  - React+Redux GUI with 3D force-directed visualization  
  - LLM agents via Model Context Protocol (MCP)

## CLI
- Stop and start the Code Story Service and MCP adapter automatically when needed  
- Trigger ingestion runs (`codestory ingest <path-or-url>`)  
- Manage ingestion jobs: start, stop, cancel, list, monitor status and progress  
- Query the graph database using:
  - Ad-hoc Cypher queries (`codestory query <cypher>`)  
  - MCP tool calls for semantic search, path finding, summaries (`codestory query <mcp>`)  
  - Natural-language queries (`codestory ask <query>`)  
- Show or update configuration settings (`codestory config show`, `codestory config <key=value>`)  
- Open the GUI in a browser (`codestory ui`)  
- Output an HTML visualization of the graph with color-coded key and 3D force-directed layout  
- Provide clear help and error messages for each command  

## GUI
- Single-page React+Redux application that:
  - Renders a 3D force-directed graph of the code knowledge graph  
  - Displays node and edge metadata on hover and click  
  - Offers an ingestion dashboard to start runs and monitor real-time progress  
  - Provides a dynamic configuration editor bound to `.env` and `.codestory.toml`  
  - Includes an MCP Playground to issue tool calls and view JSON results  
  - Features a natural-language query interface for graph questions  
  - Adapts responsively to desktop and mobile screens  
  - Wraps all CLI features in a user-friendly interface without direct CLI invocation  

## Ingestion Pipeline
- Execute workflow steps in the order specified by a configuration file  
- Start, stop, cancel, and monitor ingestion jobs via API and CLI  
- Support plugin-based workflow steps for extensibility  
- Retry failed steps or entire workflows with configurable back-off policies  
- Offer an “Ingestion Update” mode for incremental graph updates without rerunning all steps  
- Schedule jobs for future execution with `eta` or `countdown` parameters  
- Accept priority levels and enforce priority queueing for task execution  
- Define and respect dependencies between workflow steps  
- Report detailed logging, metrics, and real-time progress updates over WebSocket  
- Throttle resource usage via a Redis-backed token bucket to prevent overload  
- Automatically detect and mount repositories in Docker environments, mapping host paths to containers  

## Blarify Workflow Step
- Parse the codebase using the Blarify tool to generate AST and symbol bindings  
- Store parsed AST in the Graph Service  
- Support incremental updates for changed files  
- Estimate job status based on parsing progress  
- Run in Docker locally or in Azure Container Apps  

## FileSystem Workflow Step
- Recursively traverse repository filesystem and apply ignore patterns  
- Create `Directory` and `File` nodes with metadata (size, extension, timestamps)  
- Link filesystem nodes to AST nodes via `CONTAINS`, `IMPLEMENTS`, and `DEFINES` relationships  
- Support incremental updates and idempotent operation  
- Provide progress reporting and allow graceful cancellation  

## Summarizer Workflow Step
- Build a directed acyclic graph (DAG) of code dependencies  
- Process leaf nodes in parallel up to a configurable limit  
- Generate natural-language summaries for each AST and filesystem node  
- Compute module-level and top-level repository summaries  
- Store summaries in the Graph Service linked to relevant nodes  
- Report progress and support cancellation  

## Documentation Grapher Workflow Step
- Discover and parse documentation files (Markdown, RST, docstrings)  
- Extract entities and relationships from documentation content  
- Link documentation entities to AST, filesystem, and summary nodes in the graph  
- Store documentation graph in the Graph Service  
- Support cancellation and report progress  

## Graph Database Service
- Provide a self-hosted Neo4j 5.x backend with semantic index and vector search  
- Initialize and manage schema, constraints, indexes, and vector indexes  
- Offer synchronous and asynchronous query interfaces with automatic connection pooling  
- Expose Prometheus metrics for query performance and connection health  
- Support native vector similarity search for semantic embeddings  
- Facilitate container-based local development and Azure Container Apps deployment  

## AI Client
- Provide async/sync access to Azure OpenAI for completions, chat, and embeddings  
- Implement retry logic with exponential back-off for rate limits  
- Expose Prometheus metrics and OpenTelemetry traces  
- Support multiple models for different tasks (completions, chat, embeddings)  
- Allow parameter configuration for model selection and back-off policies  

## Configuration Module
- Load configuration from multiple sources with clear precedence: environment variables, `.env` file, `.codestory.toml`, defaults  
- Expose a strongly-typed settings interface via Pydantic models  
- Secure sensitive values with Azure KeyVault integration  
- Support hot-reloading of configuration without service restart  
- Persist configuration changes back to `.env` or `.codestory.toml`  
- Organize settings into component-specific sections  

## Code Story Service
- Expose REST API for ingestion management (`/v1/ingest`), graph queries (`/v1/query`), and natural-language ask (`/v1/ask`)  
- Provide configuration CRUD endpoints (`/v1/config`) and service control hooks (`/v1/service/start`, `/v1/service/stop`)  
- Stream real-time ingestion progress via WebSocket (`/ws/status/{job_id}`)  
- Implement authentication with Microsoft Entra ID or token-based local dev mode  
- Return JSON:API compliant payloads with `data`, `meta`, and `errors` sections  
- Expose health check (`/v1/health`) and Prometheus metrics (`/metrics`)  

## MCP Adapter
- Implement a Model Context Protocol server exposing tools:
  - `searchGraph` for code graph search  
  - `summarizeNode` for natural-language summaries  
  - `pathTo` for graph path finding  
  - `similarCode` for semantic similarity search  
- Secure all endpoints with Microsoft Entra ID authentication and enforce authorization scopes  
- Provide both gRPC and HTTP transport interfaces  
- Map tool calls to efficient Graph Service operations and format results as MCP-compatible JSON  
- Collect usage metrics and enforce rate limits  

## Infrastructure
- Provide infrastructure-as-code for local development (Docker Compose) and cloud deployment (Azure Container Apps)  
- Define container configurations, networking, persistent volumes, health checks, and secrets management  
- Support service-to-service authentication and secure protocols across environments  
- Enable observability with centralized logging, metrics, and distributed tracing  
- Facilitate scalable infrastructure with appropriate resource allocations and scaling rules  

## Documentation
- Generate API reference documentation from code docstrings for Python and TypeScript/JavaScript  
- Provide user guides for CLI and GUI usage, including installation, workflows, and troubleshooting  
- Document architecture, component interactions, data flow, and design decisions with diagrams  
- Offer developer guides for environment setup, extension, testing, and contribution processes  
- Include tutorials, examples, and a searchable documentation portal with cross-linking