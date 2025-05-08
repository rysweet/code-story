"""
Integration tests for Neo4jConnector using a real Neo4j database (Testcontainers).
"""
import pytest
from codestory.graphdb.exceptions import QueryError, TransactionError, SchemaError

# Use the fixture from conftest.py which connects to the Docker Compose Neo4j instance on non-standard port


import re

def clean_test_data(connector):
    # Remove all test nodes and relationships created by tests
    # Only remove nodes with test-specific properties or labels
    # (Assumes test nodes have unique values for 'path', 'name', etc. used in tests)
    connector.execute_query("""
        MATCH (f:File {path: 'foo.py'}) DETACH DELETE f
    """, write=True)
    connector.execute_query("""
        MATCH (c:Class {name: 'MyClass', module: 'foo'}) DETACH DELETE c
    """, write=True)
    connector.execute_query("""
        MATCH (f:Function {name: 'my_func', module: 'foo'}) DETACH DELETE f
    """, write=True)
    connector.execute_query("""
        MATCH (s:Summary {text: 'summary'}) DETACH DELETE s
    """, write=True)

@pytest.fixture(autouse=True)
def _clean_db(connector):
    clean_test_data(connector)
    yield
    clean_test_data(connector)

def test_schema_initialization(connector):
    # Should not raise
    connector.initialize_schema()

def test_basic_query_execution(connector):
    # Create a node
    connector.execute_query("CREATE (f:File {path: $path, size: $size})", {"path": "foo.py", "size": 123}, write=True)
    # Retrieve the node
    result = connector.execute_query("MATCH (f:File {path: $path}) RETURN f.size AS size", {"path": "foo.py"})
    assert result[0]["size"] == 123

def test_transaction_management(connector):
    queries = [
        "CREATE (c:Class {name: $name, module: $module})",
        "CREATE (f:Function {name: $fname, module: $module})"
    ]
    params_list = [
        {"name": "MyClass", "module": "foo"},
        {"fname": "my_func", "module": "foo"}
    ]
    connector.execute_many(queries, params_list, write=True)
    # Check both nodes exist
    res1 = connector.execute_query("MATCH (c:Class {name: 'MyClass', module: 'foo'}) RETURN c")
    res2 = connector.execute_query("MATCH (f:Function {name: 'my_func', module: 'foo'}) RETURN f")
    assert res1 and res2

def test_vector_index_and_semantic_search(connector):
    # Create a node with an embedding
    embedding = [0.1] * 1536
    connector.execute_query(
        "CREATE (s:Summary {text: $text, embedding: $embedding})",
        {"text": "summary", "embedding": embedding},
        write=True
    )
    # Create vector index (should be idempotent)
    connector.create_vector_index("Summary", "embedding", 1536)
    # Perform semantic search
    try:
        results = connector.semantic_search(embedding, "Summary", limit=1)
    except Exception as e:
        # If GDS/APOC is not available, skip with a clear message
        if re.search(r"(gds|apoc|No such function|Procedure not found)", str(e), re.IGNORECASE):
            pytest.skip(f"Vector search not available: {e}")
        raise
    assert results and "score" in results[0]

def test_error_handling(connector):
    # Invalid query should raise QueryError
    with pytest.raises(QueryError):
        connector.execute_query("INVALID CYPHER")
