# Overview

CodeStory is designed to automate codebase analysis, documentation, and semantic search for modern software projects. Its primary goal is to help teams understand, document, and query their code using a combination of static analysis, graph modeling, and AI-powered insights. By ingesting source code and related documentation, CodeStory builds a rich, queryable graph of symbols, relationships, and summaries.

The architecture centers on a modular ingestion pipeline that processes code through several steps: AST parsing (via Blarify), filesystem traversal, summarization, and documentation graphing. The resulting data is stored in a Neo4j graph database, enabling advanced queries and semantic search. The system integrates an AI client (Azure OpenAI) for code summarization and natural language interaction, and an MCPAdapter for connecting to external Model Context Protocol (MCP) services.

Key components include:
- **Pipeline:** Orchestrates code ingestion and processing steps.
- **GraphService:** Manages the Neo4j graph database and provides query APIs.
- **AIClient:** Handles AI-powered summarization and embedding.
- **MCPAdapter:** Connects to external MCP servers for advanced search and integration.

For a detailed technical breakdown, see the [Design Specification](https://github.com/your-org/codestory/blob/feature/codestory-scaffold/specs/01-design-spec.md).