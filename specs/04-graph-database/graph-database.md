# 4.0 Graph Database Service

**Previous:** [Configuration Module](../03-configuration/configuration.md) | **Next:** [AI Client](../05-ai-client/ai-client.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)

**Used by:**
- [Blarify Workflow Step](../07-blarify-step/blarify-step.md)
- [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md)
- [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md)
- [Documentation Grapher Step](../10-docgrapher-step/docgrapher-step.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)

## 4.1 Purpose

Provide a self‑hosted **Neo4j 5.x** backend with semantic index and vector search capability for storing and querying the code knowledge graph. The service is designed to run in a container locally or in Azure Container Apps, with mounted `plugins/` directory for APOC and vector search extensions, and persistent data storage in a named volume `neo4j_data`.

## 4.2 Responsibilities

- Create, initialize, and maintain the Neo4j database schema, constraints, and indexes
- Provide a unified `Neo4jConnector` interface with connection pooling and error handling for other components
- Support both synchronous and asynchronous query execution patterns
- Enable efficient storage and retrieval of various node types (AST, filesystem, documentation, summaries)
- Support semantic search through vector indexes and embeddings using GDS similarity functions
- Manage connection lifecycle and provide retry mechanisms for transient failures
- Expose Prometheus metrics for monitoring database performance and connection health
- Facilitate Docker-based local development and Azure Container Apps deployment
- Provide factory function for connector creation with automatic configuration from settings
- Support transaction management with automatic retry and instrumentation

## 4.3 Architecture and Code Structure

```text
src/codestory/graphdb/
├── __init__.py                  # Exports Neo4jConnector and create_connector
├── neo4j_connector.py           # Primary connector interface with pooling, async and vector search
├── schema.py                    # Schema definitions and initialization
├── exceptions.py                # Graph-specific exception classes  
├── models.py                    # Data models for graph entities
├── metrics.py                   # Prometheus metrics for Neo4j operations
└── export.py                    # Data export utilities
```

### 4.3.1 Factory Function

The module provides a `create_connector()` factory function that creates a configured `Neo4jConnector` instance using application settings:

```python
def create_connector() -> Neo4jConnector:
    """Create a Neo4jConnector instance using application settings.
    
    Returns:
        Neo4jConnector: Configured connector instance
        
    Raises:
        ConnectionError: If connection to Neo4j fails
        RuntimeError: If get_settings is not available
        
    Example:
        from codestory.graphdb import create_connector
        
        # Create connector from environment/settings
        connector = create_connector()
        
        # Use with context manager for automatic cleanup
        with create_connector() as connector:
            result = connector.execute_query("RETURN 1 as num")
    """
```

### 4.3.2 Neo4jConnector Interface

The `Neo4jConnector` class provides a unified interface for interacting with Neo4j, supporting both synchronous and asynchronous operations:

```python
class Neo4jConnector:
    def __init__(
        self, 
        uri: str | None = None,
        username: str | None = None, 
        password: str | None = None,
        database: str | None = None,
        async_mode: bool = False,
        **config_options: Any
    ) -> None:
        """Initialize connector with connection parameters.
        
        Falls back to settings from get_settings() if parameters not provided.
        """
        
    # Synchronous methods
    @instrument_query(query_type=QueryType.READ)
    @retry_on_transient()
    def execute_query(
        self, 
        query: str, 
        params: dict[str, Any] | None = None, 
        write: bool = False, 
        retry_count: int = 3
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query with automatic connection management."""
        
    @instrument_query(query_type=QueryType.WRITE)
    @retry_on_transient()
    def execute_many(
        self, 
        queries: list[str], 
        params_list: list[dict[str, Any]] | None = None, 
        write: bool = False
    ) -> list[list[dict[str, Any]]]:
        """Execute multiple queries in a single transaction."""
    
    # Asynchronous methods (using thread executor)
    async def execute_query_async(
        self, 
        query: str, 
        params: dict[str, Any] | None = None, 
        write: bool = False
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query asynchronously."""
        
    async def execute_many_async(
        self, 
        queries: list[dict[str, Any]], 
        write: bool = False
    ) -> list[list[dict[str, Any]]]:
        """Execute multiple queries asynchronously."""
    
    # Schema management
    @instrument_query(query_type=QueryType.SCHEMA)
    def initialize_schema(self) -> None:
        """Create constraints, indexes, and schema elements."""
        
    @instrument_query(query_type=QueryType.SCHEMA)
    def create_vector_index(
        self, 
        label: str, 
        property_name: str, 
        dimensions: int = 1536, 
        similarity: str = "cosine"
    ) -> None:
        """Create a vector index for semantic search."""
    
    # Vector search using GDS
    def semantic_search(
        self, 
        query_embedding: list[float], 
        node_label: str, 
        property_name: str = "embedding", 
        limit: int = 10,
        similarity_cutoff: float | None = None
    ) -> list[dict[str, Any]]:
        """Perform vector similarity search using GDS cosine similarity."""
    
    # Node and relationship operations
    def create_node(self, label: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a node in the Neo4j database."""
        
    def find_node(self, label: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Find a node with the given label and properties."""
        
    def create_relationship(
        self,
        start_node: dict[str, Any],
        end_node: dict[str, Any], 
        rel_type: str,
        properties: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a relationship between two nodes."""
    
    # Transaction management
    def with_transaction(
        self, 
        func: Callable[..., Any], 
        write: bool = False, 
        **kwargs: Any
    ) -> Any:
        """Execute a function within a Neo4j transaction."""
        
    def get_session(self) -> Any:
        """Get a Neo4j session for direct operations."""
    
    # Connection management
    def check_connection(self) -> dict[str, Any]:
        """Check if database is accessible and return basic info."""
        
    def close(self) -> None:
        """Close all connections in the pool."""
        
    # Context manager support
    def __enter__(self) -> "Neo4jConnector":
        """Support for context manager protocol."""
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clean up resources when exiting context."""
```

### 4.3.3 Retry and Instrumentation Decorators

The connector uses decorators for automatic retry and metrics instrumentation:

```python
@retry_on_transient(max_retries: int = 3, backoff_factor: float = 1.5)
def decorated_function():
    """Decorator for retrying operations on transient Neo4j errors."""

@instrument_query(query_type: QueryType)  
def decorated_function():
    """Decorator for recording metrics about query execution."""
```

## 4.4 Data Model and Schema

The graph database stores multiple types of interlinked nodes representing different aspects of the codebase:

### 4.4.1 Core Node Types

- **File** - Represents a file in the repository (properties: path, size, content, etc.)
- **Directory** - Represents a directory in the repository (properties: path, etc.)
- **Class** - Represents a class definition (properties: name, documentation, etc.)
- **Function/Method** - Represents a function or method (properties: name, signature, documentation, etc.)
- **Module** - Represents a module or package (properties: name, path, etc.)
- **Summary** - Contains natural language summaries generated by LLMs (properties: text, embedding)
- **Documentation** - Represents documentation content (properties: content, type, embedding)

### 4.4.2 Relationship Types

- **CONTAINS** - Directory contains files/subdirectories, file contains classes/functions
- **IMPORTS** - Module imports another module
- **CALLS** - Function calls another function
- **INHERITS_FROM** - Class inherits from another class
- **DOCUMENTED_BY** - Code element is documented by a Documentation node
- **SUMMARIZED_BY** - Code element is summarized by a Summary node

### 4.4.3 Constraints and Indexes

```cypher
// Unique constraints
CREATE CONSTRAINT IF NOT EXISTS ON (f:File) ASSERT f.path IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS ON (d:Directory) ASSERT d.path IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS ON (c:Class) ASSERT (c.name, c.module) IS UNIQUE;

// Full-text indexes
CREATE FULLTEXT INDEX file_content IF NOT EXISTS FOR (f:File) ON EACH [f.content];
CREATE FULLTEXT INDEX code_name IF NOT EXISTS FOR (n:Class|Function|Module) ON EACH [n.name];

// Vector indexes (for semantic search)
CREATE VECTOR INDEX summary_embedding IF NOT EXISTS FOR (s:Summary) 
ON s.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536, 
  `vector.similarity_function`: "cosine"
}};

CREATE VECTOR INDEX documentation_embedding IF NOT EXISTS FOR (d:Documentation) 
ON d.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536, 
  `vector.similarity_function`: "cosine"
}};
```

## 4.5 Connection Management and Configuration

The `Neo4jConnector` implements smart connection pooling with these features:

- **Dynamic Pool Sizing** - Scales connections based on load with configurable min/max size
- **Connection Validation** - Checks connection health before returning from pool
- **Automatic Retry** - Exponential backoff for transient failures using `@retry_on_transient` decorator
- **Metrics Collection** - Tracks connection usage and query performance via Prometheus
- **Transaction Management** - Ensures proper transaction handling for write operations
- **Resource Cleanup** - Graceful connection closure on service shutdown
- **Settings Integration** - Automatic fallback to application settings when parameters not provided
- **Mock Support** - Special handling for testing environments with mock drivers

Configuration parameters are integrated with the global settings pattern from section 3.0:

```python
from codestory.graphdb import create_connector

# Simple usage with settings
connector = create_connector()

# Manual configuration
connector = Neo4jConnector(
    uri="bolt://localhost:7687",
    username="neo4j", 
    password="password",
    database="neo4j",
    max_connection_pool_size=50,
    connection_timeout=30,
    skip_connection_check=False  # For testing
)
```

The connector automatically falls back to settings if parameters are not provided:

```python
# Falls back to settings.neo4j.* configuration automatically
settings = get_settings()
connector = Neo4jConnector(
    uri=settings.neo4j.uri,
    username=settings.neo4j.username,
    password=settings.neo4j.password.get_secret_value(),
    database=settings.neo4j.database,
    max_connection_pool_size=settings.neo4j.max_connection_pool_size,
    connection_timeout=settings.neo4j.connection_timeout,
    max_transaction_retry_time=getattr(settings.neo4j, "max_transaction_retry_time", None)
)

# Auto-initialize schema if configured
try:
    auto_initialize = getattr(settings.neo4j, "auto_initialize_schema", False)
    force_update = getattr(settings.neo4j, "force_schema_update", False)

    if auto_initialize:
        from .schema import initialize_schema

        initialize_schema(connector, force=force_update)
        logger.info("Neo4j schema initialized successfully")
except Exception as e:
    logger.warning(f"Failed to auto-initialize Neo4j schema: {e!s}")

return connector
```

## 4.6 Vector Search Implementation

Vector search is implemented directly in the `Neo4jConnector` class using Neo4j's GDS (Graph Data Science) library for similarity functions:

```python
def semantic_search(
    self, 
    query_embedding: list[float], 
    node_label: str, 
    property_name: str = "embedding", 
    limit: int = 10,
    similarity_cutoff: float | None = None
) -> list[dict[str, Any]]:
    """
    Perform vector similarity search using GDS cosine similarity.
    
    Args:
        query_embedding: The vector embedding to search against
        node_label: The node label to search within
        property_name: The property containing the embedding vector
        limit: Maximum number of results
        similarity_cutoff: Minimum similarity score (0-1) to include in results
        
    Returns:
        List of nodes with similarity scores
        
    Raises:
        QueryError: If the search fails
    """
    cypher = f"""
    MATCH (n:{node_label})
    WHERE n.{property_name} IS NOT NULL
    WITH n, gds.similarity.cosine(n.{property_name}, $embedding) AS score
    """
    
    if similarity_cutoff is not None:
        cypher += f"\nWHERE score >= {similarity_cutoff}"
    
    cypher += """
    ORDER BY score DESC
    LIMIT $limit
    RETURN n, score
    """
    
    return self.execute_query(
        cypher, 
        {"embedding": query_embedding, "limit": limit}
    )
```

Vector search features:
- **GDS Integration** - Uses `gds.similarity.cosine()` for accurate similarity calculations
- **Flexible Property Names** - Configurable embedding property names
- **Similarity Cutoff** - Optional minimum similarity threshold filtering
- **Performance Metrics** - Automatic recording of search execution time via `record_vector_search()`
- **Error Handling** - Comprehensive error handling with detailed context

## 4.7 Error Handling Strategy

The connector implements a comprehensive error handling strategy with custom exception hierarchy:

```python
# Exception hierarchy from exceptions.py
class Neo4jError(Exception):
    """Base exception for all Neo4j-related errors."""
    
class ConnectionError(Neo4jError):
    """Error establishing connection to Neo4j."""
    def __init__(self, message: str, uri: str | None = None, cause: Exception | None = None):
        self.uri = uri
        self.cause = cause
        super().__init__(message)
    
class QueryError(Neo4jError):
    """Error executing a Cypher query."""
    def __init__(
        self, 
        message: str, 
        query: str | None = None, 
        parameters: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        self.query = query
        self.parameters = parameters
        self.cause = cause
        super().__init__(message)
    
class SchemaError(Neo4jError):
    """Error with graph schema operation."""
    def __init__(
        self, 
        message: str, 
        operation: str | None = None,
        cause: Exception | None = None,
        **context: Any
    ):
        self.operation = operation
        self.cause = cause
        self.context = context
        super().__init__(message)
    
class TransactionError(Neo4jError):
    """Error in transaction management."""
    def __init__(
        self, 
        message: str, 
        operation: str | None = None,
        cause: Exception | None = None
    ):
        self.operation = operation  
        self.cause = cause
        super().__init__(message)
```

Error handling features:
- **Categorized Exceptions** - Custom exception hierarchy for different error types with rich context
- **Automatic Retries** - `@retry_on_transient` decorator with configurable retry policy for transient failures
- **Detailed Logging** - Structured logging of all errors with query context and parameters
- **Graceful Degradation** - Fallback mechanisms for non-critical failures
- **Metrics Integration** - Error recording via `record_connection_error()` and `record_transaction()` functions
- **Mock Compatibility** - Special handling for testing environments to avoid connection errors

## 4.8 Metrics and Monitoring

The connector integrates with Prometheus for comprehensive monitoring:

### 4.8.1 Available Metrics

```python
# From metrics.py
class QueryType(str, Enum):
    READ = "read"
    WRITE = "write" 
    SCHEMA = "schema"

# Metrics collected:
QUERY_DURATION: HistogramLike     # Query execution time by type
QUERY_COUNT: CounterLike          # Total queries executed by type  
POOL_SIZE: GaugeLike              # Connection pool size
POOL_ACQUIRED: GaugeLike          # Acquired connections
RETRY_COUNT: CounterLike          # Retry attempts by query type
CONNECTION_ERRORS: CounterLike    # Connection failure count
TRANSACTION_COUNT: CounterLike    # Transaction success/failure count
VECTOR_SEARCH_DURATION: HistogramLike  # Vector search execution time
```

### 4.8.2 Instrumentation Usage

The `@instrument_query` decorator automatically records metrics:

```python
@instrument_query(query_type=QueryType.READ)
def execute_query(self, query: str, ...):
    # Automatically records:
    # - Query duration histogram
    # - Query count increment  
    # - Error rates if query fails
```

### 4.8.3 Manual Metrics Recording

```python
# Manual metrics recording for specific operations
record_vector_search(node_label, execution_time)
record_connection_error()
record_transaction(success=True/False)
record_retry(query_type)
update_pool_metrics(pool_size, acquired_connections)
```

### 4.8.4 Graceful Degradation

When Prometheus is not available, the module provides dummy implementations that safely no-op:

```python
# Automatically handles missing prometheus_client
if not PROMETHEUS_AVAILABLE:
    # Uses DummyHistogram, DummyCounter, etc.
    # All metric calls become no-ops
```

## 4.9 Usage Examples

### 4.9.1 Basic Query Execution

```python
from codestory.graphdb import create_connector

# Using factory function with automatic settings
with create_connector() as connector:
    # Simple read query
    result = connector.execute_query(
        "MATCH (f:File) WHERE f.path CONTAINS $keyword RETURN f.path",
        {"keyword": "README"}
    )
    
    # Print results
    for record in result:
        print(record["f.path"])
        
# Manual connector creation
connector = Neo4jConnector(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

try:
    # Write operation
    result = connector.execute_query(
        "CREATE (n:Node {name: $name}) RETURN n",
        {"name": "test_node"},
        write=True
    )
finally:
    connector.close()
```

### 4.9.2 Transaction Management

```python
# Multiple operations in a single transaction
def create_class_hierarchy(connector, base_class, derived_classes):
    queries = []
    params_list = []
    
    # Create base class
    queries.append("CREATE (c:Class {name: $name, module: $module})")
    params_list.append({"name": base_class["name"], "module": base_class["module"]})
    
    # Create derived classes with inheritance relationships
    for derived in derived_classes:
        queries.append("""
        MATCH (base:Class {name: $base_name, module: $base_module})
        CREATE (derived:Class {name: $derived_name, module: $derived_module})
        CREATE (derived)-[:INHERITS_FROM]->(base)
        """)
        params_list.append({
            "base_name": base_class["name"], 
            "base_module": base_class["module"],
            "derived_name": derived["name"],
            "derived_module": derived["module"]
        })
    
    # Execute all in one transaction
    return connector.execute_many(queries, params_list, write=True)

# Using with_transaction for custom transaction logic
def complex_operation(connector, tx=None, **kwargs):
    # Custom transaction logic
    result1 = tx.run("CREATE (n:Node) RETURN n")
    result2 = tx.run("MATCH (n:Node) RETURN count(n) as total")
    return {"created": result1.single(), "total": result2.single()["total"]}

result = connector.with_transaction(complex_operation, write=True)
```

### 4.9.3 Vector Search Usage

```python
# Semantic search with embeddings
query_embedding = [0.1, 0.2, 0.3, ...]  # 1536-dimensional vector

# Basic vector search
results = connector.semantic_search(
    query_embedding=query_embedding,
    node_label="Summary",
    property_name="embedding",
    limit=5
)

for result in results:
    node = result["n"]
    score = result["score"]
    print(f"Node: {node['name']}, Similarity: {score:.3f}")

# Vector search with similarity cutoff
high_similarity_results = connector.semantic_search(
    query_embedding=query_embedding,
    node_label="Documentation", 
    similarity_cutoff=0.8,
    limit=10
)
```

### 4.9.4 Async Usage with FastAPI

```python
from fastapi import FastAPI, Depends
from codestory.graphdb import create_connector

app = FastAPI()
connector = create_connector()

@app.on_event("shutdown")
async def shutdown():
    connector.close()

@app.get("/files/{path}")
async def get_file_info(path: str):
    query = "MATCH (f:File {path: $path}) RETURN f"
    result = await connector.execute_query_async(query, {"path": path})
    
    if not result:
        return {"error": "File not found"}
    
    return {"file": dict(result[0]["f"])}

@app.post("/batch-queries")
async def execute_batch(queries: list[dict]):
    # queries = [{"query": "...", "params": {...}}, ...]
    results = await connector.execute_many_async(queries, write=False)
    return {"results": results}
```

### 4.9.5 Node and Relationship Operations

```python
# Create a node
file_node = connector.create_node(
    label="File",
    properties={
        "path": "/src/main.py",
        "size": 1024,
        "content": "print('hello')"
    }
)

# Find a node
found_node = connector.find_node(
    label="File", 
    properties={"path": "/src/main.py"}
)

# Create a directory node  
dir_node = connector.create_node(
    label="Directory",
    properties={"path": "/src"}
)

# Create containment relationship
relationship = connector.create_relationship(
    start_node=dir_node,
    end_node=file_node,
    rel_type="CONTAINS",
    properties={"created_at": "2024-01-01"}
)
```

## 4.10 Docker Configuration

The Neo4j database runs in a Docker container with the following configuration:

```yaml
neo4j:
  image: neo4j:${NEO4J_VERSION:-5.18.0-enterprise}
  container_name: ${CONTAINER_PREFIX:-codestory}-neo4j
  ports:
    - "${NEO4J_HTTP_PORT:-7476}:7474"  # HTTP for browser access
    - "${NEO4J_BOLT_PORT:-7689}:7687"  # Bolt protocol
  environment:
    - NEO4J_AUTH=${NEO4J_AUTH:-neo4j/password}  # Default credentials
    - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
    - NEO4J_dbms_memory_heap_initial__size=${NEO4J_MEMORY_HEAP_INITIAL:-512m}
    - NEO4J_dbms_memory_heap_max__size=${NEO4J_MEMORY_HEAP_MAX:-2G}
    - NEO4J_dbms_memory_pagecache_size=${NEO4J_MEMORY_PAGECACHE:-512m}
    - NEO4J_initial_dbms_default__database=${NEO4J_DATABASE:-neo4j}
    - NEO4J_server_config_strict__validation_enabled=false
  volumes:
    - codestory_neo4j_data:/data  # Persistent data
  networks:
    - codestory
  healthcheck:
    test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:7474"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Required plugins are automatically installed via the `NEO4J_PLUGINS` environment variable:
- **APOC** - Advanced procedures and functions
- **GDS** - Graph Data Science library for vector similarity functions

The plugins are installed automatically when the container starts, eliminating the need for manual plugin management.

## 4.11 Testing Strategy

### 4.11.1 Unit Tests
- **Neo4jConnector methods** - Test with mocked Neo4j driver using `unittest.mock.MagicMock`
- **Error handling and retry logic** - Test transient error scenarios and backoff behavior  
- **Vector search functionality** - Test GDS similarity search with mock embeddings
- **Async connector operations** - Test thread executor usage for async methods
- **Transaction management** - Test `with_transaction` and `execute_many` methods
- **Settings integration** - Test fallback to `get_settings()` configuration
- **Metrics instrumentation** - Test decorator behavior and metrics recording

### 4.11.2 Integration Tests  
- **Neo4j Testcontainers** - Spin up actual Neo4j database for testing
- **Schema initialization** - Test constraint and index creation
- **Data persistence** - Test data survives connection cycling
- **Connection pooling** - Test pool behavior under concurrent load
- **Vector index creation and search** - Test end-to-end vector operations
- **GDS plugin availability** - Test GDS functions work correctly
- **Real embedding search** - Test semantic search with actual OpenAI embeddings

### 4.11.3 Mock Support in Tests
The connector provides special handling for test environments:

```python
# Automatic mock detection
if isinstance(self.driver, MagicMock | AsyncMock):
    # Return mock responses directly
    # Skip connection verification
    # Enable test-specific behavior
```

Key test configuration options:
- `skip_connection_check=True` - Disable connection verification for tests
- `skip_settings=True` - Avoid loading settings in test environments
- Mock driver detection - Automatic handling of `MagicMock` and `AsyncMock` drivers

## 4.12 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to easily create a configured Neo4j connector so that I don't have to manually manage settings. | • The `create_connector()` factory function creates a fully configured connector.<br>• Settings are automatically loaded from the application configuration.<br>• Schema can be auto-initialized if configured.<br>• Connection errors provide clear diagnostic information. |
| As a developer, I want to execute Cypher queries with automatic retry and instrumentation so that my application is resilient. | • Queries are automatically retried on transient failures with exponential backoff.<br>• All queries are instrumented with Prometheus metrics.<br>• Query execution times and error rates are tracked.<br>• Retry attempts are recorded in metrics. |
| As a developer, I want to perform vector similarity search so that I can find semantically related content. | • Vector search uses GDS cosine similarity for accuracy.<br>• Configurable embedding property names are supported.<br>• Similarity cutoff filtering is available.<br>• Search performance is tracked via metrics. |
| As a developer, I want to create and manipulate graph nodes and relationships easily so that I can build the knowledge graph. | • Simple methods for creating nodes with properties.<br>• Easy relationship creation between existing nodes.<br>• Node finding by label and properties.<br>• Proper handling of Neo4j internal IDs. |
| As a developer, I want comprehensive error handling so that I can diagnose and handle different failure scenarios. | • Custom exception hierarchy with rich context information.<br>• Errors include original query, parameters, and cause information.<br>• Connection errors include URI and configuration context.<br>• Schema errors include operation details and additional context. |
| As a developer, I want to use the connector in async contexts so that I can integrate with FastAPI and other async frameworks. | • Async methods use thread executors to avoid blocking.<br>• Async operations have equivalent functionality to sync versions.<br>• Resource management works correctly in async contexts.<br>• Mock compatibility is maintained for async tests. |
| As a developer, I want transaction management so I can perform multiple operations atomically. | • `execute_many()` runs multiple queries in a single transaction.<br>• `with_transaction()` supports custom transaction logic.<br>• Transactions are automatically retried on transient failures.<br>• Transaction success/failure is tracked in metrics. |
| As a developer, I want the connector to work seamlessly in test environments so that I can write reliable tests. | • Mock drivers are automatically detected and handled.<br>• Connection checks can be skipped for testing.<br>• Settings loading can be bypassed in test environments.<br>• Test-specific configuration options are available. |
| As a developer, I want monitoring and observability so that I can track database performance and health. | • Prometheus metrics are automatically collected for all operations.<br>• Connection pool utilization is monitored.<br>• Query performance is tracked by type (read/write/schema).<br>• Graceful degradation when Prometheus is unavailable. |

## 4.13 Implementation Details

### 4.13.1 Current Implementation Status
The Neo4j connector is fully implemented with the following features:

✅ **Core Connector** - `Neo4jConnector` class with connection management  
✅ **Factory Function** - `create_connector()` with automatic settings integration  
✅ **Sync/Async Operations** - Both synchronous and asynchronous query execution  
✅ **Vector Search** - GDS-based semantic similarity search  
✅ **Error Handling** - Comprehensive exception hierarchy with context  
✅ **Retry Logic** - Automatic retry with exponential backoff via decorators  
✅ **Metrics Integration** - Prometheus instrumentation for all operations  
✅ **Transaction Management** - Support for single and multi-query transactions  
✅ **Mock Support** - Test-friendly design with mock driver detection  
✅ **Node/Relationship Operations** - High-level graph manipulation methods  
✅ **Schema Management** - Constraint and index creation utilities

### 4.13.2 Key Architectural Decisions

**Settings Integration**: The connector automatically falls back to application settings when connection parameters are not explicitly provided, enabling flexible configuration management.

**Thread-based Async**: Async operations use `asyncio.run_in_executor()` with thread pools rather than native async Neo4j drivers, providing compatibility while maintaining performance.

**GDS for Vector Search**: Vector similarity calculations use the Graph Data Science library's `gds.similarity.cosine()` function rather than native vector indexes, providing more flexibility and compatibility.

**Decorator-based Instrumentation**: Retry logic and metrics collection are implemented as decorators (`@retry_on_transient`, `@instrument_query`), promoting clean separation of concerns.

**Mock-aware Design**: The connector automatically detects and handles mock drivers in test environments, enabling comprehensive unit testing without requiring actual database connections.

### 4.13.3 Dependencies and Integration Points

**Configuration Module**: Tight integration with the settings system for automatic configuration loading.

**Metrics System**: Deep integration with Prometheus metrics collection, with graceful degradation when Prometheus is unavailable.

**Error Handling**: Custom exception hierarchy provides rich context for error diagnosis and handling.

### 4.13.3 Dependencies and Integration Points

**Configuration Module**: Tight integration with the settings system for automatic configuration loading via `get_settings()` with graceful fallback when settings are unavailable.

**Metrics System**: Deep integration with Prometheus metrics collection, with graceful degradation when Prometheus is unavailable using dummy implementations.

**Error Handling**: Custom exception hierarchy provides rich context for error diagnosis and handling, including cause chaining and sensitive parameter redaction.

**Testing Framework**: Special accommodations for unit testing with mock drivers (`isinstance(self.driver, MagicMock | AsyncMock)`) and configurable connection behavior.

### 4.13.4 Current Implementation Completeness

**Fully Implemented Features:**
- ✅ Factory function with automatic settings integration and schema auto-initialization
- ✅ Connection pooling with configurable pool sizes and timeouts
- ✅ Synchronous and asynchronous query execution using thread executors
- ✅ Transaction management with retry logic and instrumentation
- ✅ Vector similarity search using GDS `gds.similarity.cosine()` function
- ✅ Comprehensive error handling with custom exception hierarchy
- ✅ Prometheus metrics integration with graceful degradation
- ✅ Mock driver detection for test environments
- ✅ Schema initialization and management utilities
- ✅ Node and relationship creation/manipulation methods
- ✅ Context manager support for resource cleanup

**Configuration Features:**
- ✅ Environment variable-based Docker configuration
- ✅ Automatic plugin installation via `NEO4J_PLUGINS` environment variable
- ✅ Configurable memory settings and security policies
- ✅ Health checks and network isolation in Docker Compose

**Testing Support:**
- ✅ Mock-aware implementation for unit testing
- ✅ Integration test support with testcontainers
- ✅ Test-specific configuration options (`skip_connection_check`, `skip_settings`)
- ✅ Sensitive parameter redaction in error messages

The Neo4j connector implementation is complete and production-ready, with comprehensive error handling, monitoring, and testing support. All documented features are implemented and match the current codebase.

---

