"""Integration tests for Neo4j connector using a test container."""

import os
import time

import pytest

from codestory.graphdb.exceptions import (
    TransactionError,
)
from codestory.graphdb.models import DirectoryNode, FileNode
from codestory.graphdb.neo4j_connector import Neo4jConnector


def test_connection(neo4j_connector: Neo4jConnector) -> None:
    """Test basic connection to Neo4j."""
    # Simple query to verify connection
    result = neo4j_connector.execute_query("RETURN 1 as num")
    assert result[0]["num"] == 1


def test_create_and_retrieve_nodes(neo4j_connector: Neo4jConnector) -> None:
    """Test creating and retrieving nodes."""
    # Create test nodes
    file_node = FileNode(
        path="/test/file.py",
        name="file.py",
        extension="py",
        size=1024,
        content="print('hello')",
        # Note: not using metadata for now as Neo4j doesn't support nested properties directly
    )

    dir_node = DirectoryNode(path="/test", name="test")

    # Create nodes in database
    file_query = """
    CREATE (f:File {
        path: $path,
        name: $name, 
        extension: $extension,
        size: $size,
        content: $content
    })
    RETURN f
    """
    file_params = {
        "path": file_node.path,
        "name": file_node.name,
        "extension": file_node.extension,
        "size": file_node.size,
        "content": file_node.content,
    }

    dir_query = """
    CREATE (d:Directory {
        path: $path,
        name: $name
    })
    RETURN d
    """
    dir_params = {"path": dir_node.path, "name": dir_node.name}

    neo4j_connector.execute_query(file_query, file_params, write=True)
    neo4j_connector.execute_query(dir_query, dir_params, write=True)

    # Create relationship
    rel_query = """
    MATCH (d:Directory {path: $dir_path})
    MATCH (f:File {path: $file_path})
    CREATE (d)-[r:CONTAINS]->(f)
    RETURN r
    """
    rel_params = {"dir_path": dir_node.path, "file_path": file_node.path}
    neo4j_connector.execute_query(rel_query, rel_params, write=True)

    # Retrieve and verify file node
    result = neo4j_connector.execute_query(
        "MATCH (f:File {path: $path}) RETURN f", {"path": file_node.path}
    )
    assert len(result) == 1
    assert result[0]["f"]["path"] == file_node.path
    assert result[0]["f"]["name"] == file_node.name
    assert result[0]["f"]["extension"] == file_node.extension

    # Retrieve and verify relationship
    result = neo4j_connector.execute_query(
        """
        MATCH (d:Directory {path: $dir_path})-[r:CONTAINS]->(f:File {path: $file_path})
        RETURN type(r) as rel_type
    """,
        rel_params,
    )
    assert len(result) == 1
    assert result[0]["rel_type"] == "CONTAINS"


def test_transaction_management(neo4j_connector: Neo4jConnector) -> None:
    """Test transaction management with execute_many."""
    # Create test queries
    queries = [
        "CREATE (n:Test {id: $id, name: $name}) RETURN n",
        "CREATE (n:Test {id: $id, name: $name}) RETURN n",
        "CREATE (n:Test {id: $id, name: $name}) RETURN n",
    ]

    params_list = [
        {"id": 1, "name": "Test 1"},
        {"id": 2, "name": "Test 2"},
        {"id": 3, "name": "Test 3"},
    ]

    # Execute queries in a single transaction
    results = neo4j_connector.execute_many(queries, params_list, write=True)
    assert len(results) == 3

    # Verify all nodes were created
    count_result = neo4j_connector.execute_query("MATCH (n:Test) RETURN count(n) AS count")
    assert count_result[0]["count"] == 3


def test_transaction_rollback(neo4j_connector: Neo4jConnector) -> None:
    """Test transaction rollback on error."""
    # Create test queries with an intentional error in the middle
    queries = [
        "CREATE (n:TestRollback {id: $id}) RETURN n",
        "CREATE (n:TestRollback {id: $id}) RETURN INVALID_FUNCTION()",  # Error
        "CREATE (n:TestRollback {id: $id}) RETURN n",
    ]

    params_list = [{"id": 1}, {"id": 2}, {"id": 3}]

    # Execute queries - should fail and roll back
    with pytest.raises(TransactionError):
        neo4j_connector.execute_many(queries, params_list, write=True)

    # Verify no nodes were created (transaction rolled back)
    count_result = neo4j_connector.execute_query("MATCH (n:TestRollback) RETURN count(n) AS count")
    assert count_result[0]["count"] == 0


def test_schema_verification(neo4j_connector: Neo4jConnector) -> None:
    """Test schema verification functionality."""
    # Create constraints directly for this test
    neo4j_connector.execute_query(
        "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
        write=True,
    )

    neo4j_connector.execute_query(
        "CREATE CONSTRAINT directory_path IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE",
        write=True,
    )

    neo4j_connector.execute_query(
        "CREATE INDEX file_extension_idx IF NOT EXISTS FOR (f:File) ON (f.extension)",
        write=True,
    )

    # Check that the constraints exist
    constraints_result = neo4j_connector.execute_query("SHOW CONSTRAINTS")
    for constraint in constraints_result:
        if constraint.get("name") == "file_path":
            assert constraint.get("labelsOrTypes")[0] == "File"
            assert constraint.get("properties")[0] == "path"
        elif constraint.get("name") == "directory_path":
            assert constraint.get("labelsOrTypes")[0] == "Directory"
            assert constraint.get("properties")[0] == "path"

    # Check that the index exists
    indexes_result = neo4j_connector.execute_query("SHOW INDEXES")
    for index in indexes_result:
        if index.get("name") == "file_extension_idx":
            assert index.get("labelsOrTypes")[0] == "File"
            assert index.get("properties")[0] == "extension"


def test_vector_search(neo4j_connector: Neo4jConnector) -> None:
    """Test vector similarity search functionality using Neo4j GDS."""
    # First verify GDS plugin is available - this test requires GDS
    try:
        check_query = "RETURN gds.version() AS version"
        result = neo4j_connector.execute_query(check_query)
        print(f"Using GDS version: {result[0]['version']}")
    except Exception as e:
        pytest.skip(
            f"Graph Data Science plugin not available: {e!s}. This test requires GDS plugin."
        )

    # Create test nodes with embeddings
    embedding1 = [0.1, 0.2, 0.3, 0.4]
    embedding2 = [0.5, 0.6, 0.7, 0.8]
    embedding3 = [0.9, 0.8, 0.7, 0.6]

    # Clear any existing nodes first
    neo4j_connector.execute_query(
        "MATCH (n:VectorNode) DETACH DELETE n",
        write=True,
    )

    # Create nodes with test embeddings
    neo4j_connector.execute_query(
        """
        CREATE (n:VectorNode {name: 'Node1', embedding: $embedding})
    """,
        {"embedding": embedding1},
        write=True,
    )

    neo4j_connector.execute_query(
        """
        CREATE (n:VectorNode {name: 'Node2', embedding: $embedding})
    """,
        {"embedding": embedding2},
        write=True,
    )

    neo4j_connector.execute_query(
        """
        CREATE (n:VectorNode {name: 'Node3', embedding: $embedding})
    """,
        {"embedding": embedding3},
        write=True,
    )

    # First drop any existing index with the same name to avoid conflicts
    try:
        neo4j_connector.execute_query(
            "DROP INDEX node_embedding IF EXISTS",
            write=True,
        )
    except Exception as e:
        # Ignore errors when dropping index
        print(f"Warning: Failed to drop existing index: {e!s}")

    # Create the vector index
    neo4j_connector.execute_query(
        """
        CREATE VECTOR INDEX node_embedding
        FOR (n:VectorNode)
        ON (n.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 4,
            `vector.similarity_function`: 'cosine'
        }}
    """,
        write=True,
    )
    # Wait for index to be fully available
    time.sleep(2)

    # Test similarity search
    # Query with embedding similar to Node3
    query_embedding = [0.95, 0.85, 0.75, 0.65]

    results = neo4j_connector.semantic_search(
        query_embedding=query_embedding,
        node_label="VectorNode",
        property_name="embedding",
        limit=3,
    )

    # Assert results contain all nodes, sorted by similarity
    assert len(results) == 3

    # First result should be Node3 (most similar)
    assert results[0]["n"]["name"] == "Node3"

    # Results should be sorted by score (descending)
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"]
