# 12.0 MCP Adapter

**Previous:** [Code Story Service](../11-code-story-service/code-story-service.md) | **Next:** [CLI](../13-cli/cli.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)

**Used by:**
- [GUI](../14-gui/gui.md)
- External LLM tools (Claude Code, GitHub Copilot)

## 12.1 Purpose

The **MCP Adapter** serves as a Model Context Protocol server that exposes the Code Story graph database to LLM agents in a secure, structured way. It translates natural language or tool-based queries from agents into graph operations, enabling AI systems to efficiently extract knowledge from and reason about codebases. The adapter follows the [MCP specification](https://github.com/microsoft/modelcontextprotocol) and is secured through Microsoft Entra ID integration.

## 12.2 Responsibilities

- Implement a fully MCP-compliant server exposing graph data through standardized tools
- Secure all endpoints with Microsoft Entra ID (Azure AD) authentication
- Translate agent tool calls into efficient graph operations
- Map between high-level semantic operations and low-level Cypher queries
- Provide vector search capabilities for semantic similarity
- Support both gRPC and HTTP transport protocols
- Limit agent operations based on authorization scope
- Collect usage metrics and enforce rate limits
- Ensure consistent serialization of graph structures into MCP-compatible formats

## 12.3 Architecture and Code Structure

```text
src/codestory_mcp/
├── __init__.py                  # Package exports
├── server.py                    # MCP server implementation
├── tools/                       # Tool implementations
│   ├── __init__.py              # Tool registration
│   ├── search_graph.py          # Graph search operations
│   ├── summarize_node.py        # Node summarization
│   ├── path_to.py               # Path finding between nodes
│   └── similar_code.py          # Semantic similarity search
├── auth/                        # Authentication handling
│   ├── __init__.py
│   ├── entra_validator.py       # JWT validation for Microsoft Entra ID
│   └── scope_manager.py         # Authorization scope handling
├── adapters/                    # Service adapters
│   ├── __init__.py
│   ├── graph_service.py         # Adapter to Graph Service
│   └── openai_service.py        # Adapter to OpenAI Client
└── utils/
    ├── __init__.py
    ├── serializers.py           # Graph data serialization
    ├── metrics.py               # Prometheus metrics collection
    └── config.py                # MCP-specific configuration
```

### 12.3.1 MCP Tools Implementation

The MCP Adapter exposes a set of standardized tools that agents can use to interact with the code graph:

```python
class SearchGraphTool(BaseTool):
    """Tool for searching the code graph using various criteria."""
    
    name = "searchGraph"
    description = "Search for nodes in the code graph by name, type, or semantic similarity"
    
    parameters = {
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
    
    async def __call__(self, params: dict) -> dict:
        """Execute graph search with the given parameters."""
        query = params.get("query")
        node_types = params.get("node_types", [])
        limit = params.get("limit", 10)
        
        # Delegate to graph service for actual search
        results = await self.graph_service.search(
            query=query,
            node_types=node_types,
            limit=limit
        )
        
        # Format results according to MCP specification
        return {
            "matches": [
                {
                    "id": node.id,
                    "type": node.labels[0],
                    "name": node.get("name", ""),
                    "path": node.get("path", ""),
                    "properties": node.properties,
                    "score": score
                }
                for node, score in results
            ]
        }
```

### 12.3.2 Authentication Flow

Authentication follows the [Model Context Protocol authentication pattern](https://den.dev/blog/auth-modelcontextprotocol-entra-id/), leveraging Microsoft Entra ID:

```python
class EntraValidator:
    """JWT token validator for Microsoft Entra ID."""
    
    def __init__(self, tenant_id: str, audience: str):
        self.tenant_id = tenant_id
        self.audience = audience
        self.jwks_client = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        )
        
    async def validate_token(self, token: str) -> dict:
        """Validate JWT token and return claims if valid."""
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                options={"verify_signature": True}
            )
            
            # Verify required scopes are present
            self._verify_scopes(claims)
            
            return claims
            
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    def _verify_scopes(self, claims: dict) -> None:
        """Verify the token contains required scopes."""
        # Extract scopes from claims
        scopes = claims.get("scp", "").split()
        
        # Ensure at least one required scope is present
        required_scopes = {"code-story.read", "code-story.query"}
        if not any(scope in required_scopes for scope in scopes):
            raise AuthorizationError("Token lacks required scopes")
```

## 12.4 MCP Tool Specifications

| Tool Name | Description | Parameters | Result Structure |
|-----------|-------------|------------|------------------|
| `searchGraph` | Search for code elements using name, type, or semantic similarity. | `query` (string), `node_types` (array, optional), `limit` (integer, optional) | Array of matching nodes with scores |
| `summarizeNode` | Generate a natural language summary of a code element. | `node_id` (string), `include_context` (boolean, optional) | Summary text and references |
| `pathTo` | Find paths between two code elements. | `from_id` (string), `to_id` (string), `max_paths` (integer, optional) | Array of paths with nodes and relationships |
| `similarCode` | Find semantically similar code to a given snippet. | `code` (string), `limit` (integer, optional) | Array of similar code elements with similarity scores |

## 12.5 Configuration and Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_PORT` | No | `8001` | Port for the MCP server |
| `MCP_HOST` | No | `0.0.0.0` | Host address to bind |
| `MCP_WORKERS` | No | `4` | Number of worker processes |
| `AZURE_TENANT_ID` | Yes | - | Microsoft Entra ID tenant ID |
| `AZURE_CLIENT_ID` | Yes | - | Client ID for the MCP adapter |
| `AUTH_ENABLED` | No | `true` | Enable/disable authentication (for development) |
| `CODE_STORY_SERVICE_URL` | Yes | - | URL of the Code Story service |

## 12.6 Integration with Model Context Protocol

The MCP Adapter implements both the gRPC and HTTP interfaces defined in the Model Context Protocol specification:

- **gRPC Service**: Implements `ToolCallService` for efficient binary communication
- **HTTP Endpoints**: REST API exposing the same functionality for broader compatibility
- **OpenAPI Documentation**: Auto-generated at `/docs` endpoint
- **Health Check**: Available at `/health` endpoint

Example MCP client usage:

```python
from modelcontextprotocol import ToolCallClient

# Connect to MCP Adapter
client = ToolCallClient(
    host="localhost",
    port=8001,
    credentials=AccessTokenCredential("your_access_token")
)

# Call a tool
response = await client.call_tool(
    "searchGraph",
    {
        "query": "findAll classes implementing Serializable",
        "limit": 5
    }
)

# Process results
for match in response["matches"]:
    print(f"Found: {match['name']} ({match['type']}) - Score: {match['score']}")
```

## 12.7 Configuring AI Agents to Use Code Story MCP

### 12.7.1 Claude Code Integration

To configure Claude Code to use the Code Story MCP server:

1. First, obtain an access token for the MCP server:

```bash
# Using the CLI to get a token (in development mode)
export MCP_TOKEN=$(codestory auth token)
```

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

### 12.7.2 GitHub Copilot Integration

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

## 12.8 Docker Configuration

```yaml
mcp:
  build:
    context: .
    dockerfile: infra/docker/Dockerfile.mcp
  ports:
    - "8001:8001"
  environment:
    - CODE_STORY_SERVICE_URL=http://service:8000
    - AUTH_ENABLED=${AUTH_ENABLED:-true}
    - AZURE_TENANT_ID=${AZURE_TENANT_ID}
    - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
    - MCP_WORKERS=4
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  depends_on:
    - service
```

## 12.9 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As an LLM agent, I want to query the code graph so I can answer questions about code structure. | • The `searchGraph` tool accepts natural language queries.<br>• Results include relevant code elements with metadata.<br>• Query results are sorted by relevance score. |
| As an LLM agent, I want to find paths between code elements so I can understand dependencies. | • The `pathTo` tool finds connections between two nodes.<br>• Multiple path options are returned when available.<br>• Path results include all intermediary nodes and relationships. |
| As a developer, I want secure agent access to my code graph so unauthorized users can't access sensitive information. | • All endpoints require valid authentication tokens.<br>• Tokens are validated against Microsoft Entra ID.<br>• Appropriate scopes are required for authorization.<br>• Failed authentication attempts are logged. |
| As a system administrator, I want to monitor MCP Adapter usage so I can optimize resources. | • Prometheus metrics track tool calls, response times, and error rates.<br>• Request logs include correlation IDs for tracing.<br>• Health check endpoint provides service status. |
| As a developer, I want the MCP Adapter to integrate with my agent framework so my agents can leverage code understanding. | • Standard MCP interfaces are fully implemented.<br>• Both gRPC and HTTP endpoints work correctly.<br>• Documentation at `/docs` shows available tools and usage. |
| As a developer using Claude Code, I want to connect it to Code Story so I can get intelligent code assistance. | • Claude Code can be configured to use the MCP server.<br>• Authentication works correctly with the token system.<br>• Claude can efficiently query code structure information. |
| As a developer using GitHub Copilot, I want to connect it to Code Story so I can get repository-aware responses. | • GitHub Copilot can be configured to use the MCP server.<br>• The plugin configuration works with environment variables.<br>• Copilot can access Code Story tools through natural language requests. |

## 12.10 Testing Strategy

- **Unit Tests**
  - Test each tool implementation with mocked graph service
  - Verify token validation logic with mock JWTs
  - Test serialization/deserialization of graph data
  - Test error handling for invalid inputs

- **Integration Tests**
  - Test with actual Code Story Service (in container)
  - Verify tool call execution flow end-to-end
  - Test authentication with valid and invalid tokens
  - Benchmark performance with realistic queries

- **Security Tests**
  - Validate token handling and JWT parsing
  - Test authorization scope enforcement
  - Ensure sensitive information is properly protected

- **Agent Integration Tests**
  - Verify Claude Code can successfully call tools
  - Test GitHub Copilot plugin configuration
  - Validate complete question-answering workflows

## 12.11 Implementation Steps

1. **Set up MCP server foundation**
   - Install Model Context Protocol libraries
   - Implement basic HTTP and gRPC server structure
   - Define tool interfaces and registration mechanism
   - Set up health check and metrics endpoints

2. **Implement authentication**
   - Create Entra ID JWT validator
   - Implement scope verification
   - Add authentication middleware
   - Create development mode bypass for local testing

3. **Develop core tools**
   - Implement `searchGraph` tool
   - Implement `pathTo` tool  
   - Implement `summarizeNode` tool
   - Implement `similarCode` tool

4. **Create Code Story Service adapter**
   - Implement client for Code Story API
   - Map tool parameters to service requests
   - Transform service responses to tool responses

5. **Add metrics and observability**
   - Implement Prometheus metrics collection
   - Add structured logging
   - Set up distributed tracing with OpenTelemetry

6. **Create Docker container**
   - Create Dockerfile with multi-stage build
   - Configure environment variables
   - Add health check and resource limits

7. **Develop agent integration**
   - Create documentation for Claude Code configuration
   - Create GitHub Copilot plugin configuration
   - Test integrations with various prompt patterns

8. **Write comprehensive tests**
   - Unit tests for each component
   - Integration tests with Neo4j and Code Story Service
   - Performance benchmarks for common operations

9. **Create documentation**
   - Generate OpenAPI documentation
   - Create usage examples for different agent types
   - Document authentication flow and token acquisition

10. **Verification and Review**
    - Run all unit, integration, and agent integration tests
    - Verify test coverage meets targets for all components
    - Run linting and static analysis on all code
    - Test with actual MCP clients (Claude Code, GitHub Copilot)
    - Perform thorough code review against requirements and MCP specification
    - Test all error handling paths and authentication flows
    - Verify security of token handling and authentication
    - Test performance of tool calls with realistic queries
    - Validate compatibility with different agent frameworks
    - Make necessary adjustments based on review findings
    - Re-run all tests after any changes
    - Document discovered issues and their resolutions
    - Create detailed PR for final review

---

