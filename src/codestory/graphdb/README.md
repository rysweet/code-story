# Graph Database Module

This module provides a comprehensive interface to interact with Neo4j graph databases for the CodeStory project. It allows storing and querying code representations as knowledge graphs.

## Features

- **Connection Management**: Efficient connection pooling with automatic resource cleanup
- **Transaction Support**: Atomic operations with proper error handling and retries
- **Vector Similarity Search**: Semantic search using Neo4j's vector indexing
- **Schema Management**: Automatic creation and verification of constraints and indexes
- **Metrics Collection**: Prometheus metrics for monitoring operations
- **Export Utilities**: Export graph data in various formats (JSON, CSV, Cypher)
- **Async Support**: Both synchronous and asynchronous API
- **Error Handling**: Detailed error information with sensitive data redaction

## Components

- `Neo4jConnector`: Core class for interacting with Neo4j
- `Models`: Pydantic models for nodes and relationships
- `Schema`: Schema management functions
- `Export`: Utilities for exporting graph data
- `Metrics`: Prometheus metrics collection
- `Exceptions`: Specialized exception hierarchy

## Usage Examples

### Basic Connection

```python
from src.codestory.graphdb import Neo4jConnector, create_connector

# Create from explicit parameters
connector = Neo4jConnector(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# Or create from environment/settings
connector = create_connector()

# Use with context manager for automatic cleanup
with Neo4jConnector() as connector:
    result = connector.execute_query("RETURN 1 as num")
    print(result)  # [{"num": 1}]
```

### Executing Queries

```python
# Read query
nodes = connector.execute_query(
    "MATCH (n:File) WHERE n.path CONTAINS $pattern RETURN n",
    {"pattern": ".py"}
)

# Write query
result = connector.execute_query(
    "CREATE (n:File {path: $path, name: $name}) RETURN n",
    {"path": "/test/file.py", "name": "file.py"},
    write=True
)

# Multiple queries in a transaction
queries = [
    {
        "query": "CREATE (n:Class {name: $name}) RETURN n",
        "params": {"name": "MyClass"}
    },
    {
        "query": "CREATE (n:Function {name: $name}) RETURN n", 
        "params": {"name": "my_function"}
    }
]
results = connector.execute_many(queries)
```

### Working with Models

```python
from src.codestory.graphdb import FileNode, DirectoryNode, ContainsRelationship

# Create node models
file_node = FileNode(
    path="/test/file.py",
    name="file.py",
    extension="py",
    content="print('hello')"
)

dir_node = DirectoryNode(
    path="/test",
    name="test"
)

# Create relationship
relationship = ContainsRelationship(
    source=dir_node,
    target=file_node
)

# Store in database
file_query = """
CREATE (f:File {
    path: $path,
    name: $name, 
    extension: $extension,
    content: $content
})
RETURN f
"""
connector.execute_query(file_query, file_node.model_dump(), write=True)
```

### Vector Similarity Search

```python
# Search for semantically similar nodes
results = connector.semantic_search(
    query_embedding=[0.1, 0.2, 0.3, ...],  # Vector of floats
    node_label="Document",
    property_name="embedding",
    limit=10,
    similarity_cutoff=0.7
)

for result in results:
    print(f"Node: {result['node']['name']}, Score: {result['score']}")
```

### Schema Management

```python
from src.codestory.graphdb import initialize_schema, verify_schema

# Initialize schema (constraints, indexes)
initialize_schema(connector)

# Verify schema status
status = verify_schema(connector)
for category, elements in status.items():
    for element, exists in elements.items():
        print(f"{category}.{element}: {'✓' if exists else '✗'}")
```

### Exporting Data

```python
from src.codestory.graphdb import export_graph_data, export_cypher_script

# Export all data to JSON
files = export_graph_data(
    connector=connector,
    output_dir="/path/to/export",
    file_format="json"
)
print(f"Nodes exported to: {files['nodes']}")
print(f"Relationships exported to: {files['relationships']}")

# Export as Cypher script
script_path = export_cypher_script(
    connector=connector,
    output_path="/path/to/export/backup.cypher"
)
```

## Integration with Docker

The module includes Docker Compose configuration for running Neo4j in development and testing environments. Use the following commands:

```bash
# Start Neo4j container
docker-compose up -d neo4j

# Run integration tests
./scripts/setup_test_db.sh
pytest tests/integration/test_graphdb/
```

## Error Handling

The module provides detailed error information while protecting sensitive data:

```python
from src.codestory.graphdb import Neo4jError, QueryError

try:
    connector.execute_query("INVALID QUERY")
except QueryError as e:
    print(f"Query error: {e.message}")
    print(f"Query: {e.details['query']}")
    print(f"Cause: {e.details['cause']}")
```