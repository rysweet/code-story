# MCP Adapter Developer Guide

The Model Context Protocol (MCP) Adapter provides a standardized interface for AI agents (such as Claude Code or GitHub Copilot) to query the Code Story knowledge graph. This guide explains how to set up, configure, and use the MCP adapter with different agent frameworks.

## Overview

The MCP Adapter implements the [Model Context Protocol specification](https://github.com/microsoft/modelcontextprotocol), which defines a standard way for language models to access external tools and data sources. The adapter exposes the Code Story knowledge graph through a set of standardized tools that agents can use to:

- Search the code graph
- Summarize code elements
- Find paths between code elements
- Search for semantically similar code

## Available Tools

The MCP Adapter exposes the following tools:

| Tool Name | Description | Parameters | Result Format |
|-----------|-------------|------------|---------------|
| `searchGraph` | Search for code elements using name, type, or semantic similarity | `query` (string), `node_types` (array, optional), `limit` (integer, optional) | Array of matching nodes with scores |
| `summarizeNode` | Generate a natural language summary of a code element | `node_id` (string), `include_context` (boolean, optional) | Summary text and node metadata |
| `pathTo` | Find paths between two code elements | `from_id` (string), `to_id` (string), `max_paths` (integer, optional), `include_explanation` (boolean, optional) | Array of paths with nodes and relationships |
| `similarCode` | Find semantically similar code to a given snippet | `code` (string), `limit` (integer, optional) | Array of similar code elements with similarity scores |

## Running the MCP Adapter

### Using Docker Compose

The easiest way to run the MCP Adapter is using Docker Compose:

```bash
# Start the entire stack with Neo4j, Redis, Code Story Service, and MCP Adapter
docker-compose up -d

# Or to start just the MCP Adapter (if the service is already running)
docker-compose up -d mcp
```

### Running Locally

You can also run the MCP Adapter directly:

```bash
# Make sure you have activated your Python environment
poetry install

# Run the MCP Adapter
python -m codestory_mcp.main

# Or use the CLI script
codestory-mcp
```

## Configuration

The MCP Adapter can be configured using environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODE_STORY_SERVICE_URL` | Yes | - | URL of the Code Story service |
| `AUTH_ENABLED` | No | `true` | Enable/disable authentication |
| `AZURE_TENANT_ID` | Only if auth enabled | - | Microsoft Entra ID tenant ID |
| `AZURE_CLIENT_ID` | Only if auth enabled | - | Client ID for the MCP adapter |
| `API_AUDIENCE` | No | Client ID or `api://code-story` | Audience claim for JWT tokens |
| `MCP_PORT` | No | `8001` | Port for the MCP server |
| `MCP_HOST` | No | `0.0.0.0` | Host address to bind |
| `MCP_WORKERS` | No | `4` | Number of worker processes |
| `MCP_DEBUG` | No | `false` | Enable debug mode |

## Authentication

The MCP Adapter uses Microsoft Entra ID (Azure AD) for authentication. When authentication is enabled, clients must include a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The token must:
- Be issued by Microsoft Entra ID
- Have the correct audience claim matching the configured `API_AUDIENCE`
- Include the required scopes (`code-story.read` and/or `code-story.query`)

For development and testing, you can disable authentication by setting `AUTH_ENABLED=false`.

## Integrating with AI Agents

### Claude Code Integration

To configure Claude Code to use the Code Story MCP server:

1. First, obtain an access token for the MCP server (in development mode, you can use `AUTH_ENABLED=false` to skip this)

2. Create a Claude Code configuration file at `~/.claude-code/config.json`:

```json
{
  "tools": [
    {
      "name": "code-story",
      "type": "mcp",
      "endpoint": "http://localhost:8001",
      "auth": {
        "type": "bearer",
        "token": "YOUR_MCP_TOKEN"
      },
      "description": "Code Story provides semantic code analysis capabilities"
    }
  ]
}
```

3. In your Claude Code extension settings, enable the custom tools feature and reference this configuration file.

4. When using Claude Code, you can now prompt it to use Code Story tools:

```
Can you analyze the structure of my codebase using Code Story? I'm specifically interested in understanding the dependency structure of the authentication module.
```

### GitHub Copilot Integration

To configure GitHub Copilot Chat to use the Code Story MCP server:

1. Create a Copilot plugin configuration in your repository at `.github/copilot/mcp-config.json`:

```json
{
  "name": "code-story",
  "description": "Code Story provides semantic code insights",
  "version": "1.0.0",
  "mcp": {
    "endpoint": "http://localhost:8001",
    "auth": {
      "type": "bearer",
      "token": "${env:MCP_TOKEN}"
    }
  },
  "tools": [
    {
      "name": "searchGraph",
      "description": "Search the code graph for specific elements"
    },
    {
      "name": "summarizeNode",
      "description": "Get a summary of a code element"
    },
    {
      "name": "pathTo",
      "description": "Find paths between code elements"
    },
    {
      "name": "similarCode",
      "description": "Find semantically similar code"
    }
  ]
}
```

2. Add the `MCP_TOKEN` environment variable to your VS Code settings:

```json
{
  "terminal.integrated.env.windows": {
    "MCP_TOKEN": "your-mcp-token-here"
  },
  "terminal.integrated.env.osx": {
    "MCP_TOKEN": "your-mcp-token-here"
  },
  "terminal.integrated.env.linux": {
    "MCP_TOKEN": "your-mcp-token-here"
  }
}
```

3. Once configured, you can use Copilot Chat with Code Story tools:

```
/code-story searchGraph: Find all service classes in the codebase
```

or

```
@workspace Can you use code-story to help me understand the relationship between the AuthService and UserRepository?
```

## Direct API Usage

You can also interact with the MCP Adapter directly using HTTP requests:

### Get Available Tools

```http
GET /v1/tools
```

Response:
```json
{
  "tools": [
    {
      "name": "searchGraph",
      "description": "Search for nodes in the code graph by name, type, or semantic similarity",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search term or natural language description"
          },
          "node_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional filter for specific node types (e.g., 'Class', 'Function')"
          },
          "limit": {
            "type": "integer",
            "description": "Maximum number of results to return"
          }
        },
        "required": ["query"]
      }
    },
    // Other tools...
  ]
}
```

### Execute a Tool

```http
POST /v1/tools/{tool_name}
```

Example request:
```http
POST /v1/tools/searchGraph
Content-Type: application/json

{
  "query": "Find all classes implementing Serializable",
  "limit": 5
}
```

Example response:
```json
{
  "matches": [
    {
      "id": "node-123",
      "type": "Class",
      "name": "UserDTO",
      "path": "/path/to/UserDTO.java",
      "properties": {
        "implements": ["Serializable"],
        "package": "com.example.dto"
      },
      "score": 0.95
    },
    // Other matches...
  ],
  "metadata": {
    "query": "Find all classes implementing Serializable",
    "limit": 5,
    "result_count": 3
  }
}
```

### Health Check

```http
GET /v1/health
```

Response:
```json
{
  "status": "healthy"
}
```

## Troubleshooting

### Authentication Issues

If you encounter authentication issues:

1. Check that the token is valid and not expired
2. Verify that the token contains the required scopes
3. Check that the audience claim matches the configured audience
4. For development, you can disable authentication with `AUTH_ENABLED=false`

### Connection Issues

If you can't connect to the MCP server:

1. Verify that the MCP server is running (`docker-compose ps` or `ps aux | grep codestory_mcp`)
2. Check that you're using the correct port (default: 8001)
3. Ensure the Code Story service is running and accessible to the MCP server
4. Check the MCP server logs for errors (`docker-compose logs mcp` or check your terminal)

### Tool Execution Issues

If tool execution fails:

1. Check that you're providing all required parameters
2. Verify that parameter values are valid (e.g., non-empty strings, positive integers)
3. Check the MCP server logs for detailed error information
4. If using the Code Story service integration, ensure the service is healthy and responding

## Metrics and Monitoring

The MCP Adapter exposes Prometheus metrics at the `/metrics` endpoint. These metrics include:

- Tool call counts and durations
- Authentication success/failure counts
- Service API call counts and durations
- Graph operation counts
- Active connection counts

You can configure a Prometheus instance to scrape these metrics for monitoring.