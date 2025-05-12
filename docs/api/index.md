# API Reference

This section provides comprehensive documentation for Code Story's APIs and modules.

## API Organization

Code Story's API is organized into the following main components:

- [Configuration](config.md) - Configuration management and settings
- [Graph Database](graphdb.md) - Neo4j database interface and graph operations
- [Ingestion Pipeline](ingestion_pipeline.md) - Pipeline for processing codebases
- [Code Story Service](code_story_service.md) - FastAPI service endpoints
- [MCP Adapter](mcp_adapter.md) - Model Context Protocol integration

## REST API

Code Story exposes a REST API through its service component. The API provides endpoints for:

- Ingestion job management
- Graph querying
- Configuration management
- System health monitoring

### Base URL

When running locally, the API is accessible at:

```
http://localhost:8000/api/v1/
```

### Authentication

API requests require authentication using an API key or OAuth2 token, depending on configuration.

### Common Response Format

All API responses follow a common format:

```json
{
  "status": "success",
  "data": { ... },
  "errors": []
}
```

Or in case of errors:

```json
{
  "status": "error",
  "data": null,
  "errors": [
    {
      "code": "ERROR_CODE",
      "message": "Error message"
    }
  ]
}
```

## Python Client

Code Story includes a Python client for programmatic access to the service:

```python
from codestory.cli.client.service_client import ServiceClient

# Create client instance
client = ServiceClient(base_url="http://localhost:8000")

# Submit an ingestion job
job_id = client.submit_ingestion_job(
    repo_path="/path/to/repo",
    steps=["filesystem", "summarizer"]
)

# Get job status
status = client.get_job_status(job_id)
```

## WebSocket API

For real-time updates, Code Story provides a WebSocket API:

```
ws://localhost:8000/api/v1/ws/jobs/{job_id}
```

This allows clients to receive progress updates during long-running operations like ingestion jobs.

## Model Context Protocol (MCP)

The MCP adapter exposes the following tools for AI agents:

- `search_graph` - Performs graph queries
- `path_to` - Finds paths between entities
- `similar_code` - Finds semantically similar code
- `summarize_node` - Generates summaries for code entities

For details on using these tools, see the [MCP Adapter](mcp_adapter.md) documentation.