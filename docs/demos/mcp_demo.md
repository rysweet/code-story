# MCP Demo

This demonstration shows how to use the Code Story MCP (Machine Callable Packages) adapter for AI agent integration. The MCP interface allows agents to interact with code repositories programmatically.

## Installation

### Prerequisites

- Python 3.11+
- Running Neo4j database
- OpenAI API key
- Code Story service running

### Setting Up the MCP Service

```bash
# Clone the repository if you haven't already
git clone https://github.com/rysweet/code-story.git
cd code-story

# Install dependencies
pip install -e ".[mcp]"

# Start the MCP service
python -m codestory_mcp.main
```

The MCP service should now be running at http://localhost:8080.

## Configuration

Configure the MCP service using environment variables:

```bash
# Set Neo4j connection details
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="codestory"

# Set OpenAI API key for code analysis
export OPENAI_API_KEY="your-openai-api-key"

# Set MCP service configuration
export MCP_HOST="localhost"
export MCP_PORT=8080
export MCP_TOOLS_ENABLED=true
```

Alternatively, create a configuration file:

```bash
# Generate a default configuration file
codestory config init

# Edit the configuration file
codestory config edit
```

## Code Ingestion

Before using the MCP service, you need to ingest a code repository:

```bash
# Ingest the Code Story repository itself
codestory ingest start --path .

# Wait for ingestion to complete
codestory ingest status
```

## Using MCP with AutoGen

The MCP adapter integrates with Microsoft's AutoGen library. Here's how to use it in an AutoGen agent:

```python
# Example AutoGen script using Code Story MCP
import autogen
from autogen.agentchat.contrib.tools.mcp import register_mcp_tools

# Define the MCP endpoint
mcp_endpoint = "http://localhost:8080"

# Create an assistant agent
assistant = autogen.AssistantAgent(
    name="code_assistant",
    llm_config={
        "model": "gpt-4",
        "api_key": "your-openai-api-key",
    }
)

# Create a user proxy agent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
)

# Register MCP tools with the assistant
register_mcp_tools(
    agent=assistant,
    mcp_server_url=mcp_endpoint,
    tools=["search_graph", "path_to", "similar_code", "summarize_node"]
)

# Start a conversation with the assistant
user_proxy.initiate_chat(
    assistant,
    message="Analyze the file structure of the Code Story project. What are the main modules and their responsibilities?"
)
```

Running this script will trigger a conversation where the agent uses Code Story's MCP tools to analyze the codebase.

## Available MCP Tools

The Code Story MCP service provides the following tools:

1. **search_graph**: Search for nodes in the code graph using Cypher queries
2. **path_to**: Find the path between two nodes in the graph
3. **similar_code**: Find similar code snippets to a given one
4. **summarize_node**: Generate a detailed summary of a node

Here's how each tool is used:

### search_graph Tool

```python
# Example of using search_graph
result = assistant.execute_tool(
    "search_graph",
    {
        "query": "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path LIMIT 5"
    }
)
```

### path_to Tool

```python
# Example of using path_to
result = assistant.execute_tool(
    "path_to",
    {
        "source_node_id": "file:///src/codestory/cli/main.py",
        "target_node_id": "file:///src/codestory/config/settings.py"
    }
)
```

### similar_code Tool

```python
# Example of using similar_code
result = assistant.execute_tool(
    "similar_code",
    {
        "code_snippet": "def execute_query(self, query, params=None):",
        "limit": 3
    }
)
```

### summarize_node Tool

```python
# Example of using summarize_node
result = assistant.execute_tool(
    "summarize_node",
    {
        "node_id": "file:///src/codestory/graphdb/neo4j_connector.py"
    }
)
```

## Using MCP with GitHub Copilot in VS Code

You can also configure the Code Story MCP service as a custom tool provider for GitHub Copilot in Visual Studio Code:

1. Open VS Code and ensure you have the GitHub Copilot Chat extension installed
2. Open VS Code settings (JSON) by pressing `Ctrl+Shift+P` and selecting "Preferences: Open Settings (JSON)"
3. Add the following configuration:

```json
"github.copilot.chat.mcpServers": [
    {
        "name": "Code Story",
        "url": "http://localhost:8080",
        "descriptions": {
            "search_graph": "Search for nodes in the code graph using Cypher queries",
            "path_to": "Find the path between two nodes in the graph",
            "similar_code": "Find similar code snippets to a given one",
            "summarize_node": "Generate a detailed summary of a node"
        }
    }
]
```

4. Restart VS Code
5. Open GitHub Copilot Chat and use the `/mcp` command to access Code Story tools

Example chat prompt:
```
/mcp Code Story: summarize_node "file:///src/codestory/graphdb/neo4j_connector.py"
```

## Cleanup

When you're done with the demo:

```bash
# Stop the MCP service (Ctrl+C in the terminal where it's running)

# Optional: Clear the database
codestory query run "MATCH (n) DETACH DELETE n"
```

## Going Further

- Explore the [MCP adapter documentation](../developer_guides/mcp_adapter.md) for more details
- Check out advanced usage patterns with AutoGen
- Try creating custom MCP tools for your specific needs