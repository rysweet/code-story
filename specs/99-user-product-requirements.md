# Code Story User & Product Requirements

## Overview & Architecture
- Convert any codebase into a richly-linked knowledge graph plus natural-language summaries that developers can query through:
  - CLI with a rich command-line interface  
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
- Provide clear help and error messages for each command  

## Ingestion Pipeline
- Extensible pipeline with multiple steps:
  - **Blarify**: Parse codebase into AST and symbol bindings  
  - **FileSystem**: Traverse filesystem, create nodes, link to AST  
  - **Summarizer**: Generate natural-language summaries for nodes  
  - **Documentation Grapher**: Parse documentation files and link entities  
- Each step supports incremental updates, idempotent operations, and progress reporting  
- Pipeline can be run in parallel with configurable concurrency limits

## Blarify Workflow Step
- Parse the codebase using the Blarify tool to generate AST and symbol bindings  
- Store parsed AST in the Graph Service  
- Support incremental updates for changed files  
- Estimate job status based on parsing progress  
- not compatible with windows or macos - must run in a linux container if on those platforms

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
- Provide a self-hosted Neo4j 5.x backend with semantic index, vector search, and apoc procedures
- Initialize and manage schema, constraints, indexes, and vector indexes  
- Offer synchronous and asynchronous query interfaces with automatic connection pooling  
- Expose Prometheus metrics for query performance and connection health  
- Support native vector similarity search for semantic embeddings  
- Facilitate container-based local development

## AI Client
- Provide async/sync access to Azure OpenAI for completions, chat, and embeddings  
- Implement retry logic with exponential back-off for rate limits  
- Support multiple models for different tasks (completions, chat, embeddings)  
- Allow parameter configuration for model selection and back-off policies  

## Configuration Module
- Load configuration from multiple sources with clear precedence: environment variables, `.env` file, `.codestory.toml`, defaults  
- Expose a strongly-typed settings interface via Pydantic models  
- Secure sensitive values with Azure KeyVault integration  
- Support hot-reloading of configuration without service restart  
- Persist configuration changes back to `.env` or `.codestory.toml`  
- Organize settings into component-specific sections  

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

## Infrastructure and Testing
- ensure that the tests are always self-contained - they must manage their own dependencies and not rely on external services, preconditions, or state
- this means that tests must use shared fixtures for managing dependencies and must ensure that configuration is set up correctly when components are in containerized environments

## Documentation
- Generate API reference documentation from code docstrings for Python and TypeScript/JavaScript  
- Provide user guides for CLI and GUI usage, including installation, workflows, and troubleshooting  
- Document architecture, component interactions, data flow, and design decisions with diagrams  
- Offer developer guides for environment setup, extension, testing, and contribution processes  
- Include tutorials, examples, and an end to end demo walkthorugh that uses this codebase as an example