# CodeStory Feature Implementation Status

| Feature                        | Owner/Mode      | Tests         | Status        | Next Step                    |
|--------------------------------|-----------------|---------------|---------------|------------------------------|
| CLI (ingest, query, config)    | Code            | Planned       | Planned       | Implement CLI scaffolding    |
| Ingestion Pipeline             | Code            | Planned       | Planned       | Implement pipeline runner    |
| Blarify Integration            | Code            | Planned       | Planned       | Containerize and invoke      |
| FileSystem Step                | Code            | Planned       | Planned       | Implement traversal/linking  |
| Summarizer Step                | Code            | Planned       | Planned       | Implement summarization DAG  |
| Documentation Grapher          | Code            | Planned       | Planned       | Implement doc parsing/linking|
| Graph DB Service (Neo4j)       | Code            | Planned       | Planned       | Container setup/schema/init  |
| AI Client (Azure OpenAI)       | Code            | Planned       | Planned       | Implement client/retry logic |
| Configuration Module           | Code            | Planned       | Planned       | Implement config loader      |
| MCP Adapter (gRPC/HTTP)        | Code            | Planned       | Planned       | Implement MCP server/tools   |
| Infrastructure/Testing         | Code            | Planned       | Planned       | Write fixtures, test infra   |
| Documentation (API, guides)    | Code            | Planned       | In Progress   | Implement docs toolchain per 02-docs-spec.md |

*Legend:*
- **Owner/Mode:** Responsible mode for implementation
- **Tests:** Status of test coverage (Planned/In Progress/Done)
- **Status:** Implementation status (Planned/In Progress/Done)
- **Next Step:** Immediate next action for the feature
