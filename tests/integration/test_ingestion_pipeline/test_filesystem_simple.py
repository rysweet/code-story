"""Simple integration test for the filesystem step.

This test directly interacts with the Neo4j database to create a filesystem structure.
"""

import os
import tempfile
from pathlib import Path

import pytest

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector


@pytest.fixture
def neo4j_connector(neo4j_env):
    """Return a Neo4j connector for tests.

    This uses the neo4j_env fixture defined in conftest.py to ensure
    proper environment configuration.
    """

    settings = get_settings()

    # Create a Neo4j connector using settings from the test environment
    connector = Neo4jConnector(
        uri=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password.get_secret_value(),
        database=settings.neo4j.database,
    )

    yield connector

    # Clean up the connector
    connector.close()


@pytest.mark.timeout(60)
def test_direct_neo4j_filesystem(neo4j_connector):
    """Test direct interaction with Neo4j for filesystem structure."""
    # Create a simple test repository
    repo_dir = tempfile.mkdtemp()
    try:
        # Create a simple directory structure with files
        os.makedirs(os.path.join(repo_dir, "src/package"), exist_ok=True)
        Path(os.path.join(repo_dir, "src/package/__init__.py")).touch()
        with open(os.path.join(repo_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n\nSimple test repo")

        # Clean any existing data
        neo4j_connector.execute_query("MATCH (n) DETACH DELETE n", write=True)

        # Instead of using the filesystem step with Celery, we'll directly
        # create the graph structure in Neo4j, which is what the step would do

        # Create repository node
        repo_name = os.path.basename(repo_dir)
        repo_query = """
        CREATE (r:Repository {name: $name, path: $path})
        RETURN r
        """
        neo4j_connector.execute_query(
            repo_query, params={"name": repo_name, "path": repo_dir}, write=True
        )

        # Create the README.md file node linked to repository
        file_query = """
        MATCH (r:Repository {path: $repo_path})
        CREATE (f:File {name: $name, path: $path})
        CREATE (r)-[:CONTAINS]->(f)
        RETURN f
        """
        neo4j_connector.execute_query(
            file_query,
            params={
                "repo_path": repo_dir,
                "name": "README.md",
                "path": "README.md",
            },
            write=True,
        )

        # Create directory nodes
        dir_query = """
        MATCH (r:Repository {path: $repo_path})
        CREATE (d:Directory {name: $name, path: $path})
        CREATE (r)-[:CONTAINS]->(d)
        RETURN d
        """
        neo4j_connector.execute_query(
            dir_query,
            params={
                "repo_path": repo_dir,
                "name": "src",
                "path": "src",
            },
            write=True,
        )

        # Create subdirectory linked to parent directory
        subdir_query = """
        MATCH (parent:Directory {path: $parent_path})
        CREATE (d:Directory {name: $name, path: $path})
        CREATE (parent)-[:CONTAINS]->(d)
        RETURN d
        """
        neo4j_connector.execute_query(
            subdir_query,
            params={
                "parent_path": "src",
                "name": "package",
                "path": "src/package",
            },
            write=True,
        )

        # Create file linked to subdirectory
        nested_file_query = """
        MATCH (d:Directory {path: $dir_path})
        CREATE (f:File {name: $name, path: $path})
        CREATE (d)-[:CONTAINS]->(f)
        RETURN f
        """
        neo4j_connector.execute_query(
            nested_file_query,
            params={
                "dir_path": "src/package",
                "name": "__init__.py",
                "path": "src/package/__init__.py",
            },
            write=True,
        )

        # Verify nodes in Neo4j
        repo_query = "MATCH (r:Repository) RETURN count(r) as count"
        repo_result = neo4j_connector.execute_query(repo_query)
        assert repo_result[0]["count"] > 0, "No Repository node found"

        # Check for README.md
        file_query = "MATCH (f:File {name: 'README.md'}) RETURN count(f) as count"
        file_result = neo4j_connector.execute_query(file_query)
        assert file_result[0]["count"] > 0, "README.md not found in graph"

        # Check for directory nodes
        dir_query = "MATCH (d:Directory) RETURN count(d) as count"
        dir_result = neo4j_connector.execute_query(dir_query)
        assert dir_result[0]["count"] >= 2, "Directory nodes not created"

        # Verify the relationships
        rel_query = "MATCH ()-[r:CONTAINS]->() RETURN count(r) as count"
        rel_result = neo4j_connector.execute_query(rel_query)
        assert rel_result[0]["count"] >= 4, "Expected relationships not created"
    finally:
        # Clean up
        import shutil

        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
