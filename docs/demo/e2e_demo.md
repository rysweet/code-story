# CodeStory E2E Demo: Ingest, Query, and Summarize with MCP

This guide demonstrates a full end-to-end workflow using CodeStory's CLI and MCP integration. You'll install dependencies, ingest your codebase, and run sample MCP queries.

---

## 1. Install CodeStory and Dependencies

```sh
uv pip install -e .[dev,docs]
uv run pre-commit install
```

## 2. Ingest the Codebase

Run the CLI to ingest your project (from the repo root):

```sh
uv run codestory ingest .
```

This will parse your codebase and build the internal graph.

## 3. Run a Sample MCP `searchGraph` Query

You can use the MCP CLI or Python API. Example CLI usage:

```sh
uv run codestory mcp searchGraph --query "Settings"
```

Sample output:
```
[
  {
    "id": "codestory.config.Settings",
    "type": "class",
    "doc": "Pydantic settings for CodeStory Neo4j connection."
  }
]
```

## 4. Summarize a Node

```sh
uv run codestory mcp summarizeNode --id "codestory.config.Settings"
```

Sample output:
```
{
  "id": "codestory.config.Settings",
  "summary": "Settings is a Pydantic model for loading Neo4j connection details from environment variables or .env files."
}
```

---

## 5. Next Steps

- Explore more queries: `listNodes`, `findReferences`, etc.
- See [docs/guides/cli.md](../guides/cli.md) for advanced usage.
- For integration, use the Python API: `from codestory.mcp import MCPAdapter`
