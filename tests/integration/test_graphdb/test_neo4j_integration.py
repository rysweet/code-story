# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

import pytest

pytestmark = pytest.mark.usefixtures("unified_test_env")

"""Integration tests for Neo4j connector using a test container."""

import os
import time

import pytest

from codestory.graphdb.exceptions import (
    TransactionError,
)
from codestory.graphdb.models import DirectoryNode, FileNode
from codestory.graphdb.neo4j_connector import Neo4jConnector

# Use standardized test data factories for node creation
from tests.test_factories import FileNodeFactory, DirectoryNodeFactory

def test_connection(unified_test_env) -> None:
    """Test basic connection to Neo4j using unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)
    result = neo4j_connector.execute_query("RETURN 1 as num")
    assert result[0]["num"] == 1
    neo4j_connector.close()

def test_create_and_retrieve_nodes(unified_test_env) -> None:
    """
    Test creating and retrieving nodes in a single transaction using unified_test_env.
    """
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)

    file_node = FileNodeFactory.build()
    dir_node = DirectoryNodeFactory.build()

    def create_nodes_and_relationship(tx):
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

        tx.run(file_query, file_params)
        tx.run(dir_query, dir_params)

        rel_query = """
        MATCH (d:Directory {path: $dir_path})
        MATCH (f:File {path: $file_path})
        CREATE (d)-[r:CONTAINS]->(f)
        RETURN r
        """
        rel_params = {"dir_path": dir_node.path, "file_path": file_node.path}
        tx.run(rel_query, rel_params)

    session = neo4j_connector.driver.session(database=neo4j_connector.database)
    try:
        session.execute_write(create_nodes_and_relationship)
    finally:
        session.close()

    result = neo4j_connector.execute_query(
        "MATCH (f:File {path: $path}) RETURN f", {"path": file_node.path}
    )
    assert len(result) == 1
    assert result[0]["f"]["path"] == file_node.path
    assert result[0]["f"]["name"] == file_node.name
    assert result[0]["f"]["extension"] == file_node.extension

    result = neo4j_connector.execute_query(
        """
        MATCH (d:Directory {path: $dir_path})-[r:CONTAINS]->(f:File {path: $file_path})
        RETURN type(r) as rel_type
    """,
        {"dir_path": dir_node.path, "file_path": file_node.path},
    )
    assert len(result) == 1
    assert result[0]["rel_type"] == "CONTAINS"
    neo4j_connector.close()


def test_transaction_management(unified_test_env) -> None:
    """Test transaction management with execute_many using unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)

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

    results = neo4j_connector.execute_many(queries, params_list, write=True)
    assert len(results) == 3

    count_result = neo4j_connector.execute_query(
        "MATCH (n:Test) RETURN count(n) AS count"
    )
    assert count_result[0]["count"] == 3
    neo4j_connector.close()


def test_transaction_rollback(unified_test_env) -> None:
    """Test transaction rollback on error using unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector, TransactionError
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)

    queries = [
        "CREATE (n:TestRollback {id: $id}) RETURN n",
        "CREATE (n:TestRollback {id: $id}) RETURN INVALID_FUNCTION()",  # Error
        "CREATE (n:TestRollback {id: $id}) RETURN n",
    ]

    params_list = [{"id": 1}, {"id": 2}, {"id": 3}]

    with pytest.raises(TransactionError):
        neo4j_connector.execute_many(queries, params_list, write=True)

    count_result = neo4j_connector.execute_query(
        "MATCH (n:TestRollback) RETURN count(n) AS count"
    )
    assert count_result[0]["count"] == 0
    neo4j_connector.close()


def test_schema_verification(unified_test_env) -> None:
    """Test schema verification functionality using unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)

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

    constraints_result = neo4j_connector.execute_query("SHOW CONSTRAINTS")
    for constraint in constraints_result:
        if constraint.get("name") == "file_path":
            assert constraint.get("labelsOrTypes")[0] == "File"
            assert constraint.get("properties")[0] == "path"
        elif constraint.get("name") == "directory_path":
            assert constraint.get("labelsOrTypes")[0] == "Directory"
            assert constraint.get("properties")[0] == "path"

    indexes_result = neo4j_connector.execute_query("SHOW INDEXES")
    for index in indexes_result:
        if index.get("name") == "file_extension_idx":
            assert index.get("labelsOrTypes")[0] == "File"
            assert index.get("properties")[0] == "extension"
    neo4j_connector.close()


def test_vector_search(unified_test_env) -> None:
    """Test vector similarity search functionality using Neo4j GDS and unified_test_env."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    uri = unified_test_env.get("NEO4J__URI") or unified_test_env.get("NEO4J_URI")
    username = unified_test_env.get("NEO4J__USERNAME", "neo4j")
    password = unified_test_env.get("NEO4J__PASSWORD", "password")
    database = unified_test_env.get("NEO4J__DATABASE", "neo4j")
    neo4j_connector = Neo4jConnector(uri=uri, username=username, password=password, database=database)

    try:
        check_query = "RETURN gds.version() AS version"
        result = neo4j_connector.execute_query(check_query)
        print(f"Using GDS version: {result[0]['version']}")
    except Exception as e:
        pytest.fail(
            f"Graph Data Science plugin not available: {e!s}. This test requires GDS plugin."
        )

    embedding1 = [0.1, 0.2, 0.3, 0.4]
    embedding2 = [0.5, 0.6, 0.7, 0.8]
    embedding3 = [0.9, 0.8, 0.7, 0.6]

    neo4j_connector.execute_query(
        "MATCH (n:VectorNode) DETACH DELETE n",
        write=True,
    )

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

    try:
        neo4j_connector.execute_query(
            "DROP INDEX node_embedding IF EXISTS",
            write=True,
        )
    except Exception as e:
        print(f"Warning: Failed to drop existing index: {e!s}")

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
    time.sleep(2)

    query_embedding = [0.95, 0.85, 0.75, 0.65]

    results = neo4j_connector.semantic_search(
        query_embedding=query_embedding,
        node_label="VectorNode",
        property_name="embedding",
        limit=3,
    )

    assert len(results) == 3
    assert results[0]["n"]["name"] == "Node3"
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i + 1]["score"]
    neo4j_connector.close()
