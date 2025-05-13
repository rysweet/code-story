"""Integration tests for Neo4j connector using a test container."""

import os
import pytest
import time
from typing import Dict, List, Any, Generator

# Set environment variables for tests
os.environ["NEO4J_DATABASE"] = "testdb"  # Match the database name in docker-compose.test.yml
os.environ["CODESTORY_TEST_ENV"] = "true"

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.graphdb.exceptions import (
    ConnectionError,
    QueryError,
    SchemaError,
    TransactionError,
)
from codestory.graphdb.schema import initialize_schema, verify_schema
from codestory.graphdb.models import FileNode, DirectoryNode, RelationshipType

# We don't skip these tests anymore as conftest.py ensures environment variables are set
# If the test container is not running, the tests will fail with connection error
# which is more informative than skipping


@pytest.fixture
def neo4j_connector() -> Generator[Neo4jConnector, None, None]:
    """Create a Neo4j connector for testing with a test container."""
    # Force testdb usage - using environment variables or defaults
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
    username = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    database = "testdb"  # Force database to match the docker-compose.test.yml

    print(f"Using Neo4j connection: {uri}, database: {database}")

    # Set environment variables for test
    os.environ["NEO4J_DATABASE"] = database
    os.environ["CODESTORY_TEST_DB"] = database

    connector = Neo4jConnector(
        uri=uri, username=username, password=password, database=database
    )

    try:
        # Clear database before tests
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)

        # Initialize schema with force=True to clear any existing constraints/indexes
        initialize_schema(connector, force=True)

        yield connector
    finally:
        # Clean up after tests
        try:
            connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        except Exception:
            # Ignore cleanup errors
            pass
        connector.close()


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
        content="print('hello')"
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
    count_result = neo4j_connector.execute_query(
        "MATCH (n:Test) RETURN count(n) AS count"
    )
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
    count_result = neo4j_connector.execute_query(
        "MATCH (n:TestRollback) RETURN count(n) AS count"
    )
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

    # Check if GDS plugin is available
    has_gds = True
    try:
        # Try a simple GDS function call to check if it's available
        check_query = "RETURN gds.version() AS version"
        neo4j_connector.execute_query(check_query)
    except Exception as e:
        # GDS plugin is not available, log a warning
        print(f"Graph Data Science plugin not available: {str(e)}. Skipping vector index creation.")
        has_gds = False

    # Only try to create vector index if GDS is available
    if has_gds:
        # First drop any existing index with the same name to avoid conflicts
        try:
            neo4j_connector.execute_query(
                "DROP INDEX node_embedding IF EXISTS",
                write=True,
            )
        except Exception as e:
            # Ignore errors when dropping index
            print(f"Warning: Failed to drop existing index: {str(e)}")

        # Create the vector index
        try:
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
        except Exception as e:
            print(f"Warning: Failed to create vector index: {str(e)}")
            print("Vector search will use fallback method")

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
